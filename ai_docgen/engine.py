from __future__ import annotations

import subprocess
from pathlib import Path

from ai_docgen.analyzer import DiffAnalyzer
from ai_docgen.config import Config
from ai_docgen.outputs.base import Output
from ai_docgen.providers.base import LLMProvider
from ai_docgen.registry import DocumentEntry, ProjectEntry, Registry
from ai_docgen.renderer import DocumentRenderer, TemplateLoader

SYSTEM_PROMPT = (
    "You are a technical documentation writer. You update specific sections of documentation "
    "based on code changes. Return ONLY the updated section content — no markdown fences, "
    "no explanations, no surrounding text. Write in clear, concise English. "
    "Be accurate and specific to the actual code."
)


class DocsEngine:
    def __init__(self, repo_root: Path, provider: LLMProvider, output: Output) -> None:
        self.repo_root = repo_root
        self.provider = provider
        self.output = output
        self.config = Config.load(repo_root)
        self.renderer = DocumentRenderer()
        self.loader = TemplateLoader(
            source=self.config.templates.source,
            local_path=(
                repo_root / self.config.templates.local_path
                if self.config.templates.source == "local"
                else None
            ),
        )

    async def init(self) -> None:
        changed_files: list[Path] = []
        for doc_config in self.config.documents:
            target = self.repo_root / doc_config.target
            template_text = self.loader.load(doc_config.template)
            document = target.read_text() if target.exists() else template_text
            section_names = self.renderer.auto_section_names(template_text)
            repo_context = self.gather_repo_context()
            for section_name in section_names:
                user_prompt = (
                    f"Repository context:\n{repo_context}\n\n"
                    f"Document type: {doc_config.type}\n"
                    f"Update the '{section_name}' section with accurate, detailed information."
                )
                updated_content = await self.provider.complete(
                    system=SYSTEM_PROMPT, user=user_prompt
                )
                document = self.renderer.patch_section(
                    document, section_name, updated_content + "\n"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(document)
            changed_files.append(target)
        if changed_files:
            self.output.apply(changed_files, "docs: generate initial documentation")
        Config.mark_initialized(self.repo_root)
        self.register_in_registry()

    async def run(self, diff_text: str) -> bool:
        if not Config.is_initialized(self.repo_root):
            await self.init()
            return False
        triggers = self.config.triggers
        analyzer = DiffAnalyzer(
            diff_text=diff_text,
            trigger_paths=triggers.paths if triggers else [],
            ignore_paths=triggers.ignore if triggers else [],
        )
        if not analyzer.has_relevant_changes():
            return True
        changed_files: list[Path] = []
        diff_summary = analyzer.diff_summary()
        for doc_config in self.config.documents:
            target = self.repo_root / doc_config.target
            if not target.exists():
                continue
            document = target.read_text()
            section_names = self.renderer.auto_section_names(document)
            updated = False
            for section_name in section_names:
                user_prompt = (
                    f"Diff summary:\n{diff_summary}\n\n"
                    f"Current document:\n{document}\n\n"
                    f"Update the '{section_name}' section if the diff affects it. "
                    f"If no update is needed, return the current section content unchanged."
                )
                updated_content = await self.provider.complete(
                    system=SYSTEM_PROMPT, user=user_prompt
                )
                new_document = self.renderer.patch_section(
                    document, section_name, updated_content + "\n"
                )
                if new_document != document:
                    document = new_document
                    updated = True
            if updated:
                target.write_text(document)
                changed_files.append(target)
        if changed_files:
            self.output.apply(changed_files, "docs: update documentation")
        return False

    async def sync(self) -> None:
        for doc_config in self.config.documents:
            target = self.repo_root / doc_config.target
            template_text = self.loader.load(doc_config.template)
            document = target.read_text() if target.exists() else template_text
            section_names = self.renderer.auto_section_names(template_text)
            repo_context = self.gather_repo_context()
            for section_name in section_names:
                user_prompt = (
                    f"Repository context:\n{repo_context}\n\n"
                    f"Current document:\n{document}\n\n"
                    f"Re-sync the '{section_name}' section to be accurate and up to date."
                )
                updated_content = await self.provider.complete(
                    system=SYSTEM_PROMPT, user=user_prompt
                )
                document = self.renderer.patch_section(
                    document, section_name, updated_content + "\n"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(document)

    def gather_repo_context(self) -> str:
        lines: list[str] = [f"Repo root: {self.repo_root.name}"]
        for candidate in ["pyproject.toml", "package.json", "composer.json", "go.mod"]:
            path = self.repo_root / candidate
            if path.exists():
                lines.append(f"\n{candidate}:\n{path.read_text()[:2000]}")
                break
        src_dirs = ["app", "src", "lib"]
        for src_dir in src_dirs:
            full = self.repo_root / src_dir
            if full.exists():
                files = [str(p.relative_to(self.repo_root)) for p in full.rglob("*.py")][:20]
                lines.append(f"\nSource files in {src_dir}/: {', '.join(files)}")
                break
        return "\n".join(lines)

    def register_in_registry(self) -> None:
        registry_path = self.repo_root / self.config.registry.path
        registry = Registry(registry_path)
        try:
            remote = (
                subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=self.repo_root)
                .decode()
                .strip()
            )
        except subprocess.CalledProcessError:
            remote = ""
        registry.register(
            ProjectEntry(
                name=self.repo_root.name,
                path=str(self.repo_root),
                remote=remote,
                documents=[DocumentEntry(target=d.target) for d in self.config.documents],
            )
        )
