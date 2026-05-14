from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, select_autoescape


@dataclass
class Section:
    name: str
    is_auto: bool
    content: str
    start: int
    end: int


AUTO_OPEN = re.compile(r"<!-- AUTO:(\w+) -->")
AUTO_CLOSE = re.compile(r"<!-- /AUTO:(\w+) -->")
MANUAL_OPEN = re.compile(r"<!-- MANUAL -->")
MANUAL_CLOSE = re.compile(r"<!-- /MANUAL -->")

BUILTIN_TEMPLATES_DIR = Path(__file__).parent / "built_in_templates"


class DocumentRenderer:
    def parse_sections(self, text: str) -> list[Section]:
        sections: list[Section] = []
        lines = text.splitlines(keepends=True)
        i = 0
        while i < len(lines):
            auto_match = AUTO_OPEN.match(lines[i].strip())
            manual_match = MANUAL_OPEN.match(lines[i].strip())
            if auto_match:
                name = auto_match.group(1)
                start = i
                content_lines: list[str] = []
                i += 1
                while i < len(lines) and not AUTO_CLOSE.match(lines[i].strip()):
                    content_lines.append(lines[i])
                    i += 1
                sections.append(
                    Section(
                        name=name,
                        is_auto=True,
                        content="".join(content_lines),
                        start=start,
                        end=i,
                    )
                )
            elif manual_match:
                start = i
                content_lines = []
                i += 1
                while i < len(lines) and not MANUAL_CLOSE.match(lines[i].strip()):
                    content_lines.append(lines[i])
                    i += 1
                sections.append(
                    Section(
                        name="MANUAL",
                        is_auto=False,
                        content="".join(content_lines),
                        start=start,
                        end=i,
                    )
                )
            i += 1
        return sections

    def auto_section_names(self, text: str) -> list[str]:
        return [s.name for s in self.parse_sections(text) if s.is_auto]

    def patch_section(self, text: str, section_name: str, new_content: str) -> str:
        open_marker = f"<!-- AUTO:{section_name} -->"
        close_marker = f"<!-- /AUTO:{section_name} -->"
        if open_marker not in text:
            return text
        before, rest = text.split(open_marker, 1)
        _, after = rest.split(close_marker, 1)
        return f"{before}{open_marker}\n{new_content}{close_marker}{after}"


class TemplateLoader:
    def __init__(self, source: str = "builtin", local_path: Path | None = None) -> None:
        self.source = source
        self.local_path = local_path

    def load(self, template_name: str) -> str:
        template_path = f"{template_name}.md.j2"
        if self.source == "local" and self.local_path:
            full_path = self.local_path / template_path
            if full_path.exists():
                return full_path.read_text()
        builtin_path = BUILTIN_TEMPLATES_DIR / template_path
        if not builtin_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")
        return builtin_path.read_text()

    def render(self, template_name: str, context: dict[str, str]) -> str:
        template_content = self.load(template_name)
        env = Environment(autoescape=select_autoescape([]))
        tmpl = env.from_string(template_content)
        return tmpl.render(**context)
