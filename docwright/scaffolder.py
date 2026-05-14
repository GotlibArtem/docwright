from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

GITHUB_ACTIONS_WORKFLOW = """\
name: Update Documentation

on:
  push:
    branches: ["**"]
  pull_request:

jobs:
  docs:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ai-docgen
      - run: ai-docgen run
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          AI_DOCGEN_BASE_SHA: >-
            ${{ github.event.pull_request.base.sha || github.event.before }}
"""

GITLAB_CI_BLOCK = """
docs:
  stage: docs
  image: python:3.12
  script:
    - pip install ai-docgen
    - ai-docgen run
  variables:
    AI_DOCGEN_BASE_SHA: $CI_MERGE_REQUEST_DIFF_BASE_SHA
"""

MAKEFILE_TARGETS = """
docs:  ## init if not initialized, otherwise update
\tai-docgen run

docs-sync:  ## force re-sync all docs against current templates
\tai-docgen sync

docs-check:  ## dry-run: show what would change
\tai-docgen run --dry-run
"""


@dataclass
class ProjectProfile:
    language: str
    service_name: str
    ci: str
    package_manager: str


class Scaffolder:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def detect_profile(self) -> ProjectProfile:
        language, service_name, package_manager = self.detect_language()
        ci = self.detect_ci()
        return ProjectProfile(
            language=language,
            service_name=service_name,
            ci=ci,
            package_manager=package_manager,
        )

    def detect_language(self) -> tuple[str, str, str]:
        pyproject = self.repo_root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            match = re.search(r'name\s*=\s*"([^"]+)"', content)
            name = match.group(1) if match else self.repo_root.name
            return "python", name, "poetry"
        package_json = self.repo_root / "package.json"
        if package_json.exists():
            data = json.loads(package_json.read_text())
            return "node", str(data.get("name", self.repo_root.name)), "npm"
        composer = self.repo_root / "composer.json"
        if composer.exists():
            data = json.loads(composer.read_text())
            name = str(data.get("name", self.repo_root.name)).split("/")[-1]
            return "php", name, "composer"
        return "unknown", self.repo_root.name, "unknown"

    def detect_ci(self) -> str:
        if (self.repo_root / ".github" / "workflows").exists():
            return "github"
        if (self.repo_root / ".gitlab-ci.yml").exists():
            return "gitlab"
        return "none"

    def generate(self, profile: ProjectProfile, provider_type: str, output_mode: str) -> None:
        self.write_config(provider_type, output_mode)
        self.append_makefile_targets()
        self.write_ci_workflow(profile)

    def write_config(self, provider_type: str, output_mode: str) -> None:
        config_dir = self.repo_root / ".ai-docgen"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "ai-docgen.yml"
        if config_file.exists():
            return
        api_key_env = {
            "claude": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
        }.get(provider_type, "")
        model = {
            "claude": "claude-sonnet-4-6",
            "openai": "gpt-4o",
            "ollama": "llama3",
        }.get(provider_type, "claude-sonnet-4-6")
        config = {
            "provider": {"type": provider_type, "model": model, "api_key_env": api_key_env},
            "output": {"mode": output_mode},
            "triggers": {
                "paths": ["app/**", "src/**", "pyproject.toml", "package.json"],
                "ignore": ["tests/**", "**/*.md"],
            },
            "documents": [
                {"type": "readme", "template": "readme/default", "target": "README.md"},
            ],
            "registry": {"path": "../.ai-docgen/registry.yml"},
        }
        config_file.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True))

    def append_makefile_targets(self) -> None:
        makefile = self.repo_root / "Makefile"
        if not makefile.exists():
            makefile.write_text(MAKEFILE_TARGETS.lstrip())
            return
        content = makefile.read_text()
        if "docs:" not in content:
            makefile.write_text(content + MAKEFILE_TARGETS)

    def write_ci_workflow(self, profile: ProjectProfile) -> None:
        if profile.ci == "github":
            workflow_path = self.repo_root / ".github" / "workflows" / "docs.yml"
            if not workflow_path.exists():
                workflow_path.write_text(GITHUB_ACTIONS_WORKFLOW)
        elif profile.ci == "gitlab":
            gitlab_ci = self.repo_root / ".gitlab-ci.yml"
            content = gitlab_ci.read_text() if gitlab_ci.exists() else ""
            if "ai-docgen run" not in content:
                gitlab_ci.write_text(content + GITLAB_CI_BLOCK)
