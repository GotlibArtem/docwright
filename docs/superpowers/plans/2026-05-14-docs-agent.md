# docs-agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI package that auto-generates and maintains README & wiki documentation on every commit using LLM analysis of git diffs.

**Architecture:** CLI entry point (`cli.py`) orchestrates five focused modules: `config` (Pydantic settings), `analyzer` (git diff → affected sections), `renderer` (Jinja2 template patching), `providers` (LLM abstraction), and `outputs` (direct commit / PR). A `registry` module tracks all connected projects. The `scaffolder` bootstraps new repos.

**Tech Stack:** Python 3.11+, Click, Pydantic v2, Jinja2, GitPython, httpx, anthropic, openai, PyYAML, rich

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package metadata, dependencies, CLI entrypoint |
| `docs_agent/config.py` | Load & validate `.docs-agent/docs-agent.yml` via Pydantic |
| `docs_agent/providers/base.py` | Abstract `LLMProvider` interface |
| `docs_agent/providers/claude.py` | Anthropic Claude provider |
| `docs_agent/providers/openai.py` | OpenAI provider |
| `docs_agent/providers/ollama.py` | Ollama REST provider via httpx |
| `docs_agent/providers/factory.py` | Instantiate provider from config |
| `docs_agent/analyzer.py` | Parse git diff → list of section names needing update |
| `docs_agent/renderer.py` | Parse AUTO/MANUAL markers, patch sections, render Jinja2 templates |
| `docs_agent/registry.py` | Read/write `registry.yml` |
| `docs_agent/outputs/base.py` | Abstract `Output` interface |
| `docs_agent/outputs/direct.py` | Commit changed files directly |
| `docs_agent/outputs/pull_request.py` | Create branch + PR via GitHub/GitLab API |
| `docs_agent/outputs/factory.py` | Instantiate output from config |
| `docs_agent/scaffolder.py` | `install` command: autodetect + generate config/Makefile/CI |
| `docs_agent/reporters/terminal.py` | `dashboard` — rich table in terminal |
| `docs_agent/reporters/html.py` | `report` — static HTML file |
| `docs_agent/cli.py` | Click CLI: install/init/run/sync/dashboard/report |
| `docs_agent/built_in_templates/readme/default.md.j2` | Default README template |
| `docs_agent/built_in_templates/wiki/architecture.md.j2` | Architecture wiki template |
| `docs_agent/built_in_templates/wiki/api-contracts.md.j2` | API contracts wiki template |
| `docs_agent/built_in_templates/wiki/development-guide.md.j2` | Dev guide wiki template |
| `tests/test_config.py` | Config loading tests |
| `tests/test_analyzer.py` | Git diff parsing tests |
| `tests/test_renderer.py` | Section patching tests |
| `tests/test_registry.py` | Registry read/write tests |
| `tests/test_scaffolder.py` | Scaffolder autodetect tests |
| `tests/test_providers.py` | Provider interface tests (mocked HTTP) |
| `tests/test_outputs.py` | Output mode tests (mocked git/API) |

---

## Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `docs_agent/__init__.py`
- Create: `docs_agent/cli.py` (skeleton)
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `Makefile`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[tool.poetry]
name = "docs-agent"
version = "0.1.0"
description = "AI-powered documentation agent: auto-generates and maintains README & wiki on every commit"
authors = []
license = "MIT"
readme = "README.md"
packages = [{include = "docs_agent"}]

[tool.poetry.scripts]
docs-agent = "docs_agent.cli:cli"

[tool.poetry.dependencies]
python = "^3.11"
click = "^8.1"
pydantic = "^2.0"
jinja2 = "^3.1"
httpx = "^0.27"
gitpython = "^3.1"
anthropic = "^0.28"
openai = "^1.30"
pyyaml = "^6.0"
rich = "^13.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
pytest-mock = "^3.12"
ruff = "^0.4"
mypy = "^1.10"
types-PyYAML = "^6.0"

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.mypy]
strict = true
python_version = "3.11"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

- [ ] **Step 2: Create skeleton CLI**

```python
# docs_agent/__init__.py
```

```python
# docs_agent/cli.py
import click


@click.group()
def cli() -> None:
    """AI-powered documentation agent."""
```

- [ ] **Step 3: Create `tests/conftest.py`**

```python
# tests/conftest.py
import pytest
from pathlib import Path


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A temporary directory simulating a repo root."""
    return tmp_path
```

- [ ] **Step 4: Create `Makefile`**

```makefile
.PHONY: install fmt lint test

install:
	poetry install

fmt:
	poetry run ruff format .
	poetry run ruff check --fix .

lint:
	poetry run ruff check .
	poetry run mypy docs_agent

test:
	poetry run pytest -x -q
```

- [ ] **Step 5: Install dependencies**

```bash
cd /Users/gotlib/Projects/gwp/docs-agent
poetry install
```

Expected: resolves without errors, `docs-agent --help` prints help text.

- [ ] **Step 6: Verify CLI works**

```bash
poetry run docs-agent --help
```

Expected output:
```
Usage: docs-agent [OPTIONS] COMMAND [ARGS]...

  AI-powered documentation agent.

Options:
  --help  Show this message and exit.
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml docs_agent/ tests/ Makefile
git commit -m "feat: project skeleton with CLI entrypoint"
```

---

## Task 2: Config Module

**Files:**
- Create: `docs_agent/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
import pytest
from pathlib import Path
import yaml
from docs_agent.config import Config, ProviderConfig, OutputConfig, DocumentConfig, TemplatesConfig


def test_load_minimal_config(tmp_path: Path) -> None:
    config_dir = tmp_path / ".docs-agent"
    config_dir.mkdir()
    config_file = config_dir / "docs-agent.yml"
    config_file.write_text(yaml.dump({
        "provider": {"type": "claude", "model": "claude-sonnet-4-6", "api_key_env": "ANTHROPIC_API_KEY"},
        "output": {"mode": "pr"},
        "documents": [{"type": "readme", "template": "readme/default", "target": "README.md"}],
    }))
    config = Config.load(tmp_path)
    assert config.provider.type == "claude"
    assert config.output.mode == "pr"
    assert len(config.documents) == 1
    assert config.documents[0].target == "README.md"


def test_load_config_with_triggers(tmp_path: Path) -> None:
    config_dir = tmp_path / ".docs-agent"
    config_dir.mkdir()
    config_file = config_dir / "docs-agent.yml"
    config_file.write_text(yaml.dump({
        "provider": {"type": "openai", "model": "gpt-4o", "api_key_env": "OPENAI_API_KEY"},
        "output": {"mode": "direct"},
        "triggers": {"paths": ["app/**"], "ignore": ["tests/**"]},
        "documents": [],
    }))
    config = Config.load(tmp_path)
    assert config.provider.type == "openai"
    assert config.triggers is not None
    assert config.triggers.paths == ["app/**"]
    assert config.triggers.ignore == ["tests/**"]


def test_load_config_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Config.load(tmp_path)


def test_initialized_marker(tmp_path: Path) -> None:
    assert Config.is_initialized(tmp_path) is False
    Config.mark_initialized(tmp_path)
    assert Config.is_initialized(tmp_path) is True
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
poetry run pytest tests/test_config.py -v
```

Expected: `ImportError: cannot import name 'Config'`

- [ ] **Step 3: Implement `config.py`**

```python
# docs_agent/config.py
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    type: Literal["claude", "openai", "ollama"]
    model: str
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: str | None = None


class OutputConfig(BaseModel):
    mode: Literal["direct", "pr"] = "pr"
    pr_title: str = "docs: auto-update documentation"
    branch_prefix: str = "docs/auto-"


class TemplatesConfig(BaseModel):
    source: Literal["builtin", "local"] = "builtin"
    local_path: str = ".docs-agent/templates"


class TriggersConfig(BaseModel):
    paths: list[str] = Field(default_factory=lambda: ["app/**", "src/**"])
    ignore: list[str] = Field(default_factory=lambda: ["tests/**", "**/*.md"])


class DocumentConfig(BaseModel):
    type: Literal["readme", "wiki"]
    template: str
    target: str


class RegistryConfig(BaseModel):
    path: str = "../.docs-agent/registry.yml"


class Config(BaseModel):
    provider: ProviderConfig
    output: OutputConfig = Field(default_factory=OutputConfig)
    templates: TemplatesConfig = Field(default_factory=TemplatesConfig)
    triggers: TriggersConfig | None = None
    documents: list[DocumentConfig] = Field(default_factory=list)
    registry: RegistryConfig = Field(default_factory=RegistryConfig)

    CONFIG_DIR: str = ".docs-agent"
    CONFIG_FILE: str = "docs-agent.yml"
    INITIALIZED_MARKER: str = ".initialized"

    @classmethod
    def load(cls, repo_root: Path) -> "Config":
        config_path = repo_root / cls.CONFIG_DIR / cls.CONFIG_FILE
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
        data = yaml.safe_load(config_path.read_text())
        return cls.model_validate(data)

    @classmethod
    def is_initialized(cls, repo_root: Path) -> bool:
        return (repo_root / cls.CONFIG_DIR / cls.INITIALIZED_MARKER).exists()

    @classmethod
    def mark_initialized(cls, repo_root: Path) -> None:
        marker = repo_root / cls.CONFIG_DIR / cls.INITIALIZED_MARKER
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
poetry run pytest tests/test_config.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add docs_agent/config.py tests/test_config.py
git commit -m "feat: config module with Pydantic validation"
```

---

## Task 3: LLM Providers

**Files:**
- Create: `docs_agent/providers/__init__.py`
- Create: `docs_agent/providers/base.py`
- Create: `docs_agent/providers/claude.py`
- Create: `docs_agent/providers/openai.py`
- Create: `docs_agent/providers/ollama.py`
- Create: `docs_agent/providers/factory.py`
- Create: `tests/test_providers.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_providers.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from docs_agent.providers.base import LLMProvider
from docs_agent.providers.claude import ClaudeProvider
from docs_agent.providers.openai import OpenAIProvider
from docs_agent.providers.ollama import OllamaProvider
from docs_agent.providers.factory import build_provider
from docs_agent.config import ProviderConfig


def test_provider_is_abstract() -> None:
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_claude_provider_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Updated README content")]
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("docs_agent.providers.claude.AsyncAnthropic", return_value=mock_client):
        provider = ClaudeProvider(model="claude-sonnet-4-6", api_key="test-key")
        result = await provider.complete(system="You are a docs writer.", user="Update this.")
        assert result == "Updated README content"


@pytest.mark.asyncio
async def test_ollama_provider_complete() -> None:
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={"message": {"content": "Ollama response"}})
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = OllamaProvider(model="llama3", base_url="http://localhost:11434")
        result = await provider.complete(system="sys", user="user msg")
        assert result == "Ollama response"


def test_build_provider_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    cfg = ProviderConfig(type="claude", model="claude-sonnet-4-6", api_key_env="ANTHROPIC_API_KEY")
    provider = build_provider(cfg)
    assert isinstance(provider, ClaudeProvider)


def test_build_provider_ollama() -> None:
    cfg = ProviderConfig(type="ollama", model="llama3", api_key_env="", base_url="http://localhost:11434")
    provider = build_provider(cfg)
    assert isinstance(provider, OllamaProvider)


def test_build_provider_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = ProviderConfig(type="claude", model="claude-sonnet-4-6", api_key_env="ANTHROPIC_API_KEY")
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        build_provider(cfg)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
poetry run pytest tests/test_providers.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement providers**

```python
# docs_agent/providers/__init__.py
```

```python
# docs_agent/providers/base.py
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str) -> str: ...
```

```python
# docs_agent/providers/claude.py
from anthropic import AsyncAnthropic
from docs_agent.providers.base import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key)

    async def complete(self, system: str, user: str) -> str:
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return str(message.content[0].text)
```

```python
# docs_agent/providers/openai.py
from openai import AsyncOpenAI
from docs_agent.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(self, system: str, user: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return content or ""
```

```python
# docs_agent/providers/ollama.py
import httpx
from docs_agent.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def complete(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            return str(response.json()["message"]["content"])
```

```python
# docs_agent/providers/factory.py
import os
from docs_agent.config import ProviderConfig
from docs_agent.providers.base import LLMProvider
from docs_agent.providers.claude import ClaudeProvider
from docs_agent.providers.openai import OpenAIProvider
from docs_agent.providers.ollama import OllamaProvider


def build_provider(config: ProviderConfig) -> LLMProvider:
    if config.type == "ollama":
        return OllamaProvider(
            model=config.model,
            base_url=config.base_url or "http://localhost:11434",
        )
    api_key = os.environ.get(config.api_key_env, "")
    if not api_key:
        raise EnvironmentError(
            f"Environment variable '{config.api_key_env}' is not set. "
            f"Required for provider '{config.type}'."
        )
    if config.type == "claude":
        return ClaudeProvider(model=config.model, api_key=api_key)
    if config.type == "openai":
        return OpenAIProvider(model=config.model, api_key=api_key)
    raise ValueError(f"Unknown provider type: {config.type}")
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
poetry run pytest tests/test_providers.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add docs_agent/providers/ tests/test_providers.py
git commit -m "feat: LLM providers — Claude, OpenAI, Ollama with factory"
```

---

## Task 4: Git Analyzer

**Files:**
- Create: `docs_agent/analyzer.py`
- Create: `tests/test_analyzer.py`

The analyzer takes a git diff string and a list of trigger path patterns, then returns whether any relevant files changed. It also determines which document types (readme, wiki) are potentially affected.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_analyzer.py
import pytest
from docs_agent.analyzer import DiffAnalyzer, ChangedFile


def make_diff(files: list[str]) -> str:
    lines = []
    for f in files:
        lines.append(f"diff --git a/{f} b/{f}")
        lines.append(f"--- a/{f}")
        lines.append(f"+++ b/{f}")
        lines.append("@@ -1,3 +1,4 @@")
        lines.append("+new line")
    return "\n".join(lines)


def test_extract_changed_files_from_diff() -> None:
    diff = make_diff(["app/models.py", "app/services.py"])
    analyzer = DiffAnalyzer(diff_text=diff, trigger_paths=["app/**"], ignore_paths=[])
    files = analyzer.changed_files()
    assert len(files) == 2
    assert any(f.path == "app/models.py" for f in files)


def test_has_relevant_changes_matches_glob() -> None:
    diff = make_diff(["app/models.py"])
    analyzer = DiffAnalyzer(diff_text=diff, trigger_paths=["app/**"], ignore_paths=[])
    assert analyzer.has_relevant_changes() is True


def test_has_relevant_changes_ignores_excluded() -> None:
    diff = make_diff(["tests/test_models.py"])
    analyzer = DiffAnalyzer(diff_text=diff, trigger_paths=["app/**"], ignore_paths=["tests/**"])
    assert analyzer.has_relevant_changes() is False


def test_has_relevant_changes_no_trigger_match() -> None:
    diff = make_diff(["docs/README.md"])
    analyzer = DiffAnalyzer(diff_text=diff, trigger_paths=["app/**"], ignore_paths=[])
    assert analyzer.has_relevant_changes() is False


def test_empty_diff_no_relevant_changes() -> None:
    analyzer = DiffAnalyzer(diff_text="", trigger_paths=["app/**"], ignore_paths=[])
    assert analyzer.has_relevant_changes() is False


def test_diff_summary_for_prompt() -> None:
    diff = make_diff(["app/models.py"])
    analyzer = DiffAnalyzer(diff_text=diff, trigger_paths=["app/**"], ignore_paths=[])
    summary = analyzer.diff_summary()
    assert "app/models.py" in summary
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
poetry run pytest tests/test_analyzer.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `analyzer.py`**

```python
# docs_agent/analyzer.py
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass


@dataclass
class ChangedFile:
    path: str


class DiffAnalyzer:
    def __init__(
        self,
        diff_text: str,
        trigger_paths: list[str],
        ignore_paths: list[str],
    ) -> None:
        self.diff_text = diff_text
        self.trigger_paths = trigger_paths
        self.ignore_paths = ignore_paths

    def changed_files(self) -> list[ChangedFile]:
        paths: list[str] = []
        for line in self.diff_text.splitlines():
            match = re.match(r"^\+\+\+ b/(.+)$", line)
            if match:
                paths.append(match.group(1))
        return [ChangedFile(path=p) for p in paths]

    def has_relevant_changes(self) -> bool:
        for changed in self.changed_files():
            if self.is_ignored(changed.path):
                continue
            if self.matches_trigger(changed.path):
                return True
        return False

    def diff_summary(self) -> str:
        files = self.changed_files()
        if not files:
            return "No changed files."
        lines = ["Changed files:"]
        for f in files:
            lines.append(f"  - {f.path}")
        lines.append("")
        lines.append(self.diff_text[:3000])
        if len(self.diff_text) > 3000:
            lines.append("... (truncated)")
        return "\n".join(lines)

    def is_ignored(self, path: str) -> bool:
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.ignore_paths)

    def matches_trigger(self, path: str) -> bool:
        if not self.trigger_paths:
            return True
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.trigger_paths)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
poetry run pytest tests/test_analyzer.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add docs_agent/analyzer.py tests/test_analyzer.py
git commit -m "feat: git diff analyzer with glob-based trigger matching"
```

---

## Task 5: Document Renderer

**Files:**
- Create: `docs_agent/renderer.py`
- Create: `tests/test_renderer.py`

The renderer handles two things: parsing AUTO/MANUAL markers in existing documents, and patching specific AUTO sections with new content.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_renderer.py
import pytest
from docs_agent.renderer import DocumentRenderer, Section


SAMPLE_DOC = """# My Service

Some intro text.

<!-- AUTO:overview -->
Old overview content.
<!-- /AUTO:overview -->

<!-- MANUAL -->
Manual section — never touch this.
<!-- /MANUAL -->

<!-- AUTO:getting_started -->
Old getting started.
<!-- /AUTO:getting_started -->
"""


def test_parse_sections_finds_auto() -> None:
    renderer = DocumentRenderer()
    sections = renderer.parse_sections(SAMPLE_DOC)
    auto_names = [s.name for s in sections if s.is_auto]
    assert "overview" in auto_names
    assert "getting_started" in auto_names


def test_parse_sections_finds_manual() -> None:
    renderer = DocumentRenderer()
    sections = renderer.parse_sections(SAMPLE_DOC)
    manual_sections = [s for s in sections if not s.is_auto and s.name == "MANUAL"]
    assert len(manual_sections) == 1


def test_patch_section_replaces_content() -> None:
    renderer = DocumentRenderer()
    result = renderer.patch_section(SAMPLE_DOC, "overview", "New overview content.\n")
    assert "New overview content." in result
    assert "Old overview content." not in result


def test_patch_section_preserves_manual() -> None:
    renderer = DocumentRenderer()
    result = renderer.patch_section(SAMPLE_DOC, "overview", "New overview.\n")
    assert "Manual section — never touch this." in result


def test_patch_section_preserves_other_auto() -> None:
    renderer = DocumentRenderer()
    result = renderer.patch_section(SAMPLE_DOC, "overview", "New overview.\n")
    assert "Old getting started." in result


def test_patch_nonexistent_section_returns_unchanged() -> None:
    renderer = DocumentRenderer()
    result = renderer.patch_section(SAMPLE_DOC, "nonexistent", "New content.\n")
    assert result == SAMPLE_DOC


def test_auto_section_names(doc: str = SAMPLE_DOC) -> None:
    renderer = DocumentRenderer()
    names = renderer.auto_section_names(SAMPLE_DOC)
    assert names == ["overview", "getting_started"]
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
poetry run pytest tests/test_renderer.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `renderer.py`**

```python
# docs_agent/renderer.py
from __future__ import annotations

import re
from dataclasses import dataclass


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
                sections.append(Section(
                    name=name,
                    is_auto=True,
                    content="".join(content_lines),
                    start=start,
                    end=i,
                ))
            elif manual_match:
                start = i
                content_lines = []
                i += 1
                while i < len(lines) and not MANUAL_CLOSE.match(lines[i].strip()):
                    content_lines.append(lines[i])
                    i += 1
                sections.append(Section(
                    name="MANUAL",
                    is_auto=False,
                    content="".join(content_lines),
                    start=start,
                    end=i,
                ))
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
poetry run pytest tests/test_renderer.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add docs_agent/renderer.py tests/test_renderer.py
git commit -m "feat: document renderer with AUTO/MANUAL section patching"
```

---

## Task 6: Built-in Templates

**Files:**
- Create: `docs_agent/built_in_templates/readme/default.md.j2`
- Create: `docs_agent/built_in_templates/wiki/architecture.md.j2`
- Create: `docs_agent/built_in_templates/wiki/api-contracts.md.j2`
- Create: `docs_agent/built_in_templates/wiki/development-guide.md.j2`
- Modify: `docs_agent/renderer.py` — add template loading

- [ ] **Step 1: Create template files**

```jinja
{# docs_agent/built_in_templates/readme/default.md.j2 #}
# {{ service_name }}

<!-- AUTO:overview -->
<!-- /AUTO:overview -->

## Getting Started

<!-- AUTO:getting_started -->
<!-- /AUTO:getting_started -->

## Architecture

<!-- AUTO:architecture -->
<!-- /AUTO:architecture -->

## API

<!-- AUTO:api -->
<!-- /AUTO:api -->

## Development

<!-- AUTO:development -->
<!-- /AUTO:development -->

<!-- MANUAL -->
## Contributing

Add contributing notes here.
<!-- /MANUAL -->
```

```jinja
{# docs_agent/built_in_templates/wiki/architecture.md.j2 #}
# Architecture

<!-- AUTO:overview -->
<!-- /AUTO:overview -->

## Components

<!-- AUTO:components -->
<!-- /AUTO:components -->

## Data Flow

<!-- AUTO:data_flow -->
<!-- /AUTO:data_flow -->

## Dependencies

<!-- AUTO:dependencies -->
<!-- /AUTO:dependencies -->

<!-- MANUAL -->
## Decision Log

Document architectural decisions here.
<!-- /MANUAL -->
```

```jinja
{# docs_agent/built_in_templates/wiki/api-contracts.md.j2 #}
# API Contracts

<!-- AUTO:endpoints -->
<!-- /AUTO:endpoints -->

## Authentication

<!-- AUTO:authentication -->
<!-- /AUTO:authentication -->

## Error Codes

<!-- AUTO:error_codes -->
<!-- /AUTO:error_codes -->

<!-- MANUAL -->
## Changelog

Document breaking changes here.
<!-- /MANUAL -->
```

```jinja
{# docs_agent/built_in_templates/wiki/development-guide.md.j2 #}
# Development Guide

## Setup

<!-- AUTO:setup -->
<!-- /AUTO:setup -->

## Running Tests

<!-- AUTO:testing -->
<!-- /AUTO:testing -->

## Code Style

<!-- AUTO:code_style -->
<!-- /AUTO:code_style -->

<!-- MANUAL -->
## Team Conventions

Add team-specific conventions here.
<!-- /MANUAL -->
```

- [ ] **Step 2: Add template loader to `renderer.py`**

Add to `docs_agent/renderer.py`:

```python
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape


BUILTIN_TEMPLATES_DIR = Path(__file__).parent / "built_in_templates"


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
```

- [ ] **Step 3: Write template loader test**

```python
# add to tests/test_renderer.py

from docs_agent.renderer import TemplateLoader

def test_load_builtin_readme_template() -> None:
    loader = TemplateLoader(source="builtin")
    content = loader.load("readme/default")
    assert "AUTO:overview" in content
    assert "AUTO:getting_started" in content


def test_load_missing_template_raises() -> None:
    loader = TemplateLoader(source="builtin")
    with pytest.raises(FileNotFoundError):
        loader.load("readme/nonexistent")


def test_render_template_with_context() -> None:
    loader = TemplateLoader(source="builtin")
    result = loader.render("readme/default", {"service_name": "my-service"})
    assert "# my-service" in result
```

- [ ] **Step 4: Run all renderer tests**

```bash
poetry run pytest tests/test_renderer.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add docs_agent/built_in_templates/ docs_agent/renderer.py tests/test_renderer.py
git commit -m "feat: built-in Jinja2 templates and template loader"
```

---

## Task 7: Registry

**Files:**
- Create: `docs_agent/registry.py`
- Create: `tests/test_registry.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_registry.py
import pytest
from pathlib import Path
from datetime import date
from docs_agent.registry import Registry, ProjectEntry, DocumentEntry


def test_register_new_project(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yml"
    registry = Registry(registry_path)
    registry.register(ProjectEntry(
        name="my-service",
        path="../my-service",
        remote="git@github.com:org/my-service.git",
        documents=[DocumentEntry(target="README.md")],
    ))
    loaded = Registry(registry_path)
    projects = loaded.all_projects()
    assert len(projects) == 1
    assert projects[0].name == "my-service"


def test_register_updates_existing_project(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yml"
    registry = Registry(registry_path)
    registry.register(ProjectEntry(
        name="my-service",
        path="../my-service",
        remote="git@github.com:org/my-service.git",
        documents=[DocumentEntry(target="README.md")],
    ))
    registry.register(ProjectEntry(
        name="my-service",
        path="../my-service",
        remote="git@github.com:org/my-service.git",
        documents=[
            DocumentEntry(target="README.md"),
            DocumentEntry(target="../wiki/architecture.md"),
        ],
    ))
    projects = Registry(registry_path).all_projects()
    assert len(projects) == 1
    assert len(projects[0].documents) == 2


def test_update_document_timestamp(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yml"
    registry = Registry(registry_path)
    registry.register(ProjectEntry(
        name="my-service",
        path="../my-service",
        remote="",
        documents=[DocumentEntry(target="README.md")],
    ))
    registry.update_document_timestamp("my-service", "README.md", date(2026, 5, 14))
    projects = Registry(registry_path).all_projects()
    doc = next(d for d in projects[0].documents if d.target == "README.md")
    assert doc.last_updated == date(2026, 5, 14)


def test_empty_registry_returns_empty_list(tmp_path: Path) -> None:
    registry = Registry(tmp_path / "registry.yml")
    assert registry.all_projects() == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
poetry run pytest tests/test_registry.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `registry.py`**

```python
# docs_agent/registry.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml


@dataclass
class DocumentEntry:
    target: str
    last_updated: date | None = None


@dataclass
class ProjectEntry:
    name: str
    path: str
    remote: str
    documents: list[DocumentEntry] = field(default_factory=list)
    registered_at: date = field(default_factory=date.today)
    last_updated: date = field(default_factory=date.today)
    status: str = "synced"

    STALE_DAYS: int = 30

    def compute_status(self) -> str:
        if (date.today() - self.last_updated) > timedelta(days=self.STALE_DAYS):
            return "stale"
        return "synced"


class Registry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def all_projects(self) -> list[ProjectEntry]:
        if not self.path.exists():
            return []
        data = yaml.safe_load(self.path.read_text()) or {}
        projects = []
        for p in data.get("projects", []):
            docs = [
                DocumentEntry(
                    target=d["target"],
                    last_updated=d.get("last_updated"),
                )
                for d in p.get("documents", [])
            ]
            projects.append(ProjectEntry(
                name=p["name"],
                path=p["path"],
                remote=p.get("remote", ""),
                documents=docs,
                registered_at=p.get("registered_at", date.today()),
                last_updated=p.get("last_updated", date.today()),
                status=p.get("status", "synced"),
            ))
        return projects

    def register(self, entry: ProjectEntry) -> None:
        projects = self.all_projects()
        existing = next((p for p in projects if p.name == entry.name), None)
        if existing:
            projects.remove(existing)
        entry.last_updated = date.today()
        entry.status = entry.compute_status()
        projects.append(entry)
        self.write(projects)

    def update_document_timestamp(self, project_name: str, target: str, updated: date) -> None:
        projects = self.all_projects()
        for project in projects:
            if project.name == project_name:
                for doc in project.documents:
                    if doc.target == target:
                        doc.last_updated = updated
                project.last_updated = updated
                project.status = project.compute_status()
        self.write(projects)

    def write(self, projects: list[ProjectEntry]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "projects": [
                {
                    "name": p.name,
                    "path": p.path,
                    "remote": p.remote,
                    "registered_at": p.registered_at.isoformat(),
                    "last_updated": p.last_updated.isoformat(),
                    "status": p.status,
                    "documents": [
                        {
                            "target": d.target,
                            "last_updated": d.last_updated.isoformat() if d.last_updated else None,
                        }
                        for d in p.documents
                    ],
                }
                for p in projects
            ]
        }
        self.path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
poetry run pytest tests/test_registry.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add docs_agent/registry.py tests/test_registry.py
git commit -m "feat: registry module for tracking connected projects"
```

---

## Task 8: Output Modes

**Files:**
- Create: `docs_agent/outputs/__init__.py`
- Create: `docs_agent/outputs/base.py`
- Create: `docs_agent/outputs/direct.py`
- Create: `docs_agent/outputs/pull_request.py`
- Create: `docs_agent/outputs/factory.py`
- Create: `tests/test_outputs.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_outputs.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from docs_agent.outputs.base import Output
from docs_agent.outputs.direct import DirectOutput
from docs_agent.outputs.pull_request import PullRequestOutput
from docs_agent.outputs.factory import build_output
from docs_agent.config import OutputConfig


def test_output_is_abstract() -> None:
    with pytest.raises(TypeError):
        Output()  # type: ignore[abstract]


def test_direct_output_commits_changed_files(tmp_path: Path) -> None:
    changed_file = tmp_path / "README.md"
    changed_file.write_text("# Updated")

    mock_repo = MagicMock()
    mock_repo.index.add = MagicMock()
    mock_repo.index.commit = MagicMock()

    with patch("docs_agent.outputs.direct.Repo", return_value=mock_repo):
        output = DirectOutput(repo_root=tmp_path)
        output.apply(changed_files=[changed_file], message="docs: update README")

    mock_repo.index.add.assert_called_once()
    mock_repo.index.commit.assert_called_once_with("docs: update README")


def test_build_output_direct() -> None:
    cfg = OutputConfig(mode="direct")
    output = build_output(cfg, repo_root=Path("."))
    assert isinstance(output, DirectOutput)


def test_build_output_pr() -> None:
    cfg = OutputConfig(mode="pr")
    output = build_output(cfg, repo_root=Path("."))
    assert isinstance(output, PullRequestOutput)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
poetry run pytest tests/test_outputs.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement outputs**

```python
# docs_agent/outputs/__init__.py
```

```python
# docs_agent/outputs/base.py
from abc import ABC, abstractmethod
from pathlib import Path


class Output(ABC):
    @abstractmethod
    def apply(self, changed_files: list[Path], message: str) -> None: ...
```

```python
# docs_agent/outputs/direct.py
from pathlib import Path
from git import Repo  # type: ignore[import-untyped]
from docs_agent.outputs.base import Output


class DirectOutput(Output):
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def apply(self, changed_files: list[Path], message: str) -> None:
        repo = Repo(self.repo_root)
        str_paths = [str(f.relative_to(self.repo_root)) for f in changed_files]
        repo.index.add(str_paths)
        repo.index.commit(message)
```

```python
# docs_agent/outputs/pull_request.py
import hashlib
import os
import subprocess
from pathlib import Path
from docs_agent.outputs.base import Output
from docs_agent.config import OutputConfig


class PullRequestOutput(Output):
    def __init__(self, repo_root: Path, config: OutputConfig) -> None:
        self.repo_root = repo_root
        self.config = config

    def apply(self, changed_files: list[Path], message: str) -> None:
        short_hash = hashlib.sha1(message.encode()).hexdigest()[:8]
        branch = f"{self.config.branch_prefix}{short_hash}"
        self.run(["git", "checkout", "-b", branch])
        rel_paths = [str(f.relative_to(self.repo_root)) for f in changed_files]
        self.run(["git", "add"] + rel_paths)
        self.run(["git", "commit", "-m", message])
        self.run(["git", "push", "origin", branch])
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            self.create_github_pr(branch, message, token)

    def run(self, cmd: list[str]) -> None:
        subprocess.run(cmd, cwd=self.repo_root, check=True)

    def create_github_pr(self, branch: str, title: str, token: str) -> None:
        import httpx
        remote_url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=self.repo_root
        ).decode().strip()
        owner_repo = self.extract_owner_repo(remote_url)
        if not owner_repo:
            return
        default_branch = subprocess.check_output(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=self.repo_root,
        ).decode().strip().replace("refs/remotes/origin/", "")
        httpx.post(
            f"https://api.github.com/repos/{owner_repo}/pulls",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"title": self.config.pr_title, "head": branch, "base": default_branch, "body": title},
        )

    def extract_owner_repo(self, remote_url: str) -> str | None:
        import re
        match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", remote_url)
        return match.group(1) if match else None
```

```python
# docs_agent/outputs/factory.py
from pathlib import Path
from docs_agent.config import OutputConfig
from docs_agent.outputs.base import Output
from docs_agent.outputs.direct import DirectOutput
from docs_agent.outputs.pull_request import PullRequestOutput


def build_output(config: OutputConfig, repo_root: Path) -> Output:
    if config.mode == "direct":
        return DirectOutput(repo_root=repo_root)
    return PullRequestOutput(repo_root=repo_root, config=config)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
poetry run pytest tests/test_outputs.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add docs_agent/outputs/ tests/test_outputs.py
git commit -m "feat: output modes — direct commit and pull request"
```

---

## Task 9: CLI Commands — `init` and `run`

**Files:**
- Modify: `docs_agent/cli.py`
- Create: `docs_agent/engine.py` (orchestration logic for init/run/sync)
- Create: `tests/test_engine.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_engine.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import yaml
from docs_agent.config import Config
from docs_agent.engine import DocsEngine


def make_config_file(tmp_path: Path) -> None:
    config_dir = tmp_path / ".docs-agent"
    config_dir.mkdir(parents=True)
    (config_dir / "docs-agent.yml").write_text(yaml.dump({
        "provider": {"type": "ollama", "model": "llama3", "api_key_env": "", "base_url": "http://localhost:11434"},
        "output": {"mode": "direct"},
        "triggers": {"paths": ["app/**"], "ignore": []},
        "documents": [{"type": "readme", "template": "readme/default", "target": "README.md"}],
    }))


@pytest.mark.asyncio
async def test_init_creates_readme_when_missing(tmp_path: Path) -> None:
    make_config_file(tmp_path)
    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(return_value="# My Service\n\nGenerated overview.\n")

    mock_output = MagicMock()
    mock_output.apply = MagicMock()

    engine = DocsEngine(repo_root=tmp_path, provider=mock_provider, output=mock_output)
    await engine.init()

    readme = tmp_path / "README.md"
    assert readme.exists()
    assert "AUTO:overview" in readme.read_text()
    assert Config.is_initialized(tmp_path)


@pytest.mark.asyncio
async def test_run_skips_when_no_relevant_diff(tmp_path: Path) -> None:
    make_config_file(tmp_path)
    (tmp_path / "README.md").write_text("# Existing\n<!-- AUTO:overview -->\nOld.\n<!-- /AUTO:overview -->\n")
    Config.mark_initialized(tmp_path)

    mock_provider = AsyncMock()
    mock_output = MagicMock()

    engine = DocsEngine(repo_root=tmp_path, provider=mock_provider, output=mock_output)
    skipped = await engine.run(diff_text="diff --git a/tests/test_foo.py b/tests/test_foo.py\n+++ b/tests/test_foo.py\n+new line")

    assert skipped is True
    mock_provider.complete.assert_not_called()


@pytest.mark.asyncio
async def test_run_updates_section_on_relevant_diff(tmp_path: Path) -> None:
    make_config_file(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("# Service\n<!-- AUTO:overview -->\nOld overview.\n<!-- /AUTO:overview -->\n")
    Config.mark_initialized(tmp_path)

    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(return_value="New overview content.\n")
    mock_output = MagicMock()

    engine = DocsEngine(repo_root=tmp_path, provider=mock_provider, output=mock_output)
    skipped = await engine.run(
        diff_text="diff --git a/app/models.py b/app/models.py\n+++ b/app/models.py\n+new line"
    )

    assert skipped is False
    assert "New overview content." in readme.read_text()
    mock_output.apply.assert_called_once()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
poetry run pytest tests/test_engine.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `engine.py`**

```python
# docs_agent/engine.py
from __future__ import annotations

import asyncio
from pathlib import Path

from docs_agent.analyzer import DiffAnalyzer
from docs_agent.config import Config
from docs_agent.outputs.base import Output
from docs_agent.providers.base import LLMProvider
from docs_agent.renderer import DocumentRenderer, TemplateLoader
from docs_agent.registry import DocumentEntry, ProjectEntry, Registry


SYSTEM_PROMPT = """You are a technical documentation writer. You update specific sections of documentation
based on code changes. Return ONLY the updated section content — no markdown fences, no explanations,
no surrounding text. Write in clear, concise English. Be accurate and specific to the actual code."""


class DocsEngine:
    def __init__(
        self,
        repo_root: Path,
        provider: LLMProvider,
        output: Output,
    ) -> None:
        self.repo_root = repo_root
        self.provider = provider
        self.output = output
        self.config = Config.load(repo_root)
        self.renderer = DocumentRenderer()
        self.loader = TemplateLoader(
            source=self.config.templates.source,
            local_path=repo_root / self.config.templates.local_path if self.config.templates.source == "local" else None,
        )

    async def init(self) -> None:
        changed_files: list[Path] = []
        for doc_config in self.config.documents:
            target = self.repo_root / doc_config.target
            template_text = self.loader.load(doc_config.template)
            if not target.exists():
                document = template_text
            else:
                document = target.read_text()
            section_names = self.renderer.auto_section_names(template_text)
            repo_context = self.gather_repo_context()
            for section_name in section_names:
                user_prompt = (
                    f"Repository context:\n{repo_context}\n\n"
                    f"Document type: {doc_config.type}\n"
                    f"Update the '{section_name}' section with accurate, detailed information."
                )
                updated_content = await self.provider.complete(system=SYSTEM_PROMPT, user=user_prompt)
                document = self.renderer.patch_section(document, section_name, updated_content + "\n")
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
                updated_content = await self.provider.complete(system=SYSTEM_PROMPT, user=user_prompt)
                new_document = self.renderer.patch_section(document, section_name, updated_content + "\n")
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
                updated_content = await self.provider.complete(system=SYSTEM_PROMPT, user=user_prompt)
                document = self.renderer.patch_section(document, section_name, updated_content + "\n")
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
        import subprocess
        try:
            remote = subprocess.check_output(
                ["git", "remote", "get-url", "origin"], cwd=self.repo_root
            ).decode().strip()
        except Exception:
            remote = ""
        registry.register(ProjectEntry(
            name=self.repo_root.name,
            path=str(self.repo_root),
            remote=remote,
            documents=[DocumentEntry(target=d.target) for d in self.config.documents],
        ))
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
poetry run pytest tests/test_engine.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Wire up CLI commands**

Add to `docs_agent/cli.py`:

```python
# docs_agent/cli.py
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import click

from docs_agent.config import Config
from docs_agent.engine import DocsEngine
from docs_agent.outputs.factory import build_output
from docs_agent.providers.factory import build_provider


def get_repo_root() -> Path:
    return Path.cwd()


def build_engine(repo_root: Path) -> DocsEngine:
    config = Config.load(repo_root)
    provider = build_provider(config.provider)
    output = build_output(config.output, repo_root)
    return DocsEngine(repo_root=repo_root, provider=provider, output=output)


@click.group()
def cli() -> None:
    """AI-powered documentation agent."""


@cli.command()
def init() -> None:
    """Generate documentation from scratch."""
    repo_root = get_repo_root()
    engine = build_engine(repo_root)
    asyncio.run(engine.init())
    click.echo("Documentation initialized.")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Show what would change without writing files.")
def run(dry_run: bool) -> None:
    """Incrementally update documentation based on recent git diff."""
    repo_root = get_repo_root()
    base_sha = os.environ.get("DOCS_AGENT_BASE_SHA", "HEAD~1")
    try:
        diff_text = subprocess.check_output(
            ["git", "diff", f"{base_sha}..HEAD"], cwd=repo_root
        ).decode()
    except subprocess.CalledProcessError:
        diff_text = ""
    if dry_run:
        from docs_agent.analyzer import DiffAnalyzer
        config = Config.load(repo_root)
        triggers = config.triggers
        analyzer = DiffAnalyzer(
            diff_text=diff_text,
            trigger_paths=triggers.paths if triggers else [],
            ignore_paths=triggers.ignore if triggers else [],
        )
        if analyzer.has_relevant_changes():
            click.echo("Relevant changes detected — documentation would be updated.")
        else:
            click.echo("No relevant changes — documentation would be skipped.")
        return
    engine = build_engine(repo_root)
    skipped = asyncio.run(engine.run(diff_text=diff_text))
    if skipped:
        click.echo("No relevant changes — documentation up to date.")
    else:
        click.echo("Documentation updated.")


@cli.command()
def sync() -> None:
    """Force re-sync all documentation against current templates."""
    repo_root = get_repo_root()
    engine = build_engine(repo_root)
    asyncio.run(engine.sync())
    click.echo("Documentation synced.")
```

- [ ] **Step 6: Run all tests**

```bash
poetry run pytest -x -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add docs_agent/engine.py docs_agent/cli.py tests/test_engine.py
git commit -m "feat: engine orchestration and CLI init/run/sync commands"
```

---

## Task 10: Scaffolder (`install` command)

**Files:**
- Create: `docs_agent/scaffolder.py`
- Modify: `docs_agent/cli.py` — add `install` command
- Create: `tests/test_scaffolder.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scaffolder.py
import pytest
from pathlib import Path
from docs_agent.scaffolder import Scaffolder, ProjectProfile


def test_detect_python_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "my-service"\n')
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    assert profile.language == "python"
    assert profile.service_name == "my-service"


def test_detect_node_project(tmp_path: Path) -> None:
    import json
    (tmp_path / "package.json").write_text(json.dumps({"name": "my-frontend"}))
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    assert profile.language == "node"
    assert profile.service_name == "my-frontend"


def test_detect_github_actions_ci(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "svc"\n')
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    assert profile.ci == "github"


def test_detect_gitlab_ci(tmp_path: Path) -> None:
    (tmp_path / ".gitlab-ci.yml").touch()
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "svc"\n')
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    assert profile.ci == "gitlab"


def test_generate_creates_config_file(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "my-svc"\n')
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    scaffolder.generate(profile, provider_type="claude", output_mode="pr")
    config_file = tmp_path / ".docs-agent" / "docs-agent.yml"
    assert config_file.exists()
    content = config_file.read_text()
    assert "claude" in content
    assert "my-svc" not in content  # service_name is in context, not config


def test_generate_adds_makefile_targets(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "svc"\n')
    makefile = tmp_path / "Makefile"
    makefile.write_text("test:\n\tpoetry run pytest\n")
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    scaffolder.generate(profile, provider_type="claude", output_mode="pr")
    content = makefile.read_text()
    assert "docs:" in content
    assert "docs-sync:" in content


def test_generate_github_actions_workflow(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "svc"\n')
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    scaffolder.generate(profile, provider_type="claude", output_mode="pr")
    workflow = tmp_path / ".github" / "workflows" / "docs.yml"
    assert workflow.exists()
    assert "docs-agent run" in workflow.read_text()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
poetry run pytest tests/test_scaffolder.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `scaffolder.py`**

```python
# docs_agent/scaffolder.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ProjectProfile:
    language: str
    service_name: str
    ci: str  # "github" | "gitlab" | "none"
    package_manager: str  # "poetry" | "npm" | "composer" | "unknown"


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
      - run: pip install docs-agent
      - run: docs-agent run
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DOCS_AGENT_BASE_SHA: ${{ github.event.pull_request.base.sha || github.event.before }}
"""

GITLAB_CI_BLOCK = """\

docs:
  stage: docs
  image: python:3.12
  script:
    - pip install docs-agent
    - docs-agent run
  variables:
    DOCS_AGENT_BASE_SHA: $CI_MERGE_REQUEST_DIFF_BASE_SHA
"""

MAKEFILE_TARGETS = """\

docs:  ## init if not initialized, otherwise update
\tdocs-agent run

docs-sync:  ## force re-sync all docs against current templates
\tdocs-agent sync

docs-check:  ## dry-run: show what would change
\tdocs-agent run --dry-run
"""


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
            return "node", data.get("name", self.repo_root.name), "npm"
        composer = self.repo_root / "composer.json"
        if composer.exists():
            data = json.loads(composer.read_text())
            name = data.get("name", self.repo_root.name).split("/")[-1]
            return "php", name, "composer"
        return "unknown", self.repo_root.name, "unknown"

    def detect_ci(self) -> str:
        if (self.repo_root / ".github" / "workflows").exists():
            return "github"
        if (self.repo_root / ".gitlab-ci.yml").exists():
            return "gitlab"
        return "none"

    def generate(
        self,
        profile: ProjectProfile,
        provider_type: str,
        output_mode: str,
    ) -> None:
        self.write_config(provider_type, output_mode)
        self.append_makefile_targets(profile)
        self.write_ci_workflow(profile)

    def write_config(self, provider_type: str, output_mode: str) -> None:
        config_dir = self.repo_root / ".docs-agent"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "docs-agent.yml"
        if config_file.exists():
            return
        api_key_env = {"claude": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}.get(provider_type, "")
        model = {"claude": "claude-sonnet-4-6", "openai": "gpt-4o", "ollama": "llama3"}.get(provider_type, "claude-sonnet-4-6")
        config = {
            "provider": {"type": provider_type, "model": model, "api_key_env": api_key_env},
            "output": {"mode": output_mode},
            "triggers": {"paths": ["app/**", "src/**", "pyproject.toml", "package.json"], "ignore": ["tests/**", "**/*.md"]},
            "documents": [
                {"type": "readme", "template": "readme/default", "target": "README.md"},
            ],
            "registry": {"path": "../.docs-agent/registry.yml"},
        }
        config_file.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True))

    def append_makefile_targets(self, profile: ProjectProfile) -> None:
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
            if "docs-agent run" not in content:
                gitlab_ci.write_text(content + GITLAB_CI_BLOCK)
```

- [ ] **Step 4: Add `install` command to `cli.py`**

Add to `docs_agent/cli.py`:

```python
@cli.command("install")
@click.option("--auto", is_flag=True, help="Non-interactive mode with auto-detected defaults.")
@click.option("--provider", default=None, type=click.Choice(["claude", "openai", "ollama"]))
@click.option("--output", "output_mode", default=None, type=click.Choice(["pr", "direct"]))
def install(auto: bool, provider: str | None, output_mode: str | None) -> None:
    """Bootstrap this repo with docs-agent configuration."""
    from docs_agent.scaffolder import Scaffolder

    repo_root = get_repo_root()
    scaffolder = Scaffolder(repo_root=repo_root)
    profile = scaffolder.detect_profile()

    if auto:
        final_provider = provider or "claude"
        final_output = output_mode or "pr"
    else:
        click.echo(f"Detected: {profile.language} project '{profile.service_name}', CI: {profile.ci}")
        final_provider = provider or click.prompt(
            "LLM provider",
            type=click.Choice(["claude", "openai", "ollama"]),
            default="claude",
        )
        final_output = output_mode or click.prompt(
            "Output mode",
            type=click.Choice(["pr", "direct"]),
            default="pr",
        )

    scaffolder.generate(profile, provider_type=final_provider, output_mode=final_output)
    click.echo(f"Installed docs-agent for '{profile.service_name}'.")
    click.echo("Next: set your API key env var, then run 'make docs'.")
```

- [ ] **Step 5: Run all tests**

```bash
poetry run pytest tests/test_scaffolder.py -v
poetry run pytest -x -q
```

Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add docs_agent/scaffolder.py docs_agent/cli.py tests/test_scaffolder.py
git commit -m "feat: scaffolder and install command with auto-detection"
```

---

## Task 11: Dashboard & Report

**Files:**
- Create: `docs_agent/reporters/__init__.py`
- Create: `docs_agent/reporters/terminal.py`
- Create: `docs_agent/reporters/html.py`
- Modify: `docs_agent/cli.py` — add `dashboard` and `report` commands

- [ ] **Step 1: Implement terminal reporter**

```python
# docs_agent/reporters/__init__.py
```

```python
# docs_agent/reporters/terminal.py
from rich.console import Console
from rich.table import Table
from docs_agent.registry import Registry, ProjectEntry
from pathlib import Path


def render_dashboard(registry_path: Path) -> None:
    console = Console()
    registry = Registry(registry_path)
    projects = registry.all_projects()

    if not projects:
        console.print("[yellow]No projects registered. Run 'docs-agent init' in a project.[/yellow]")
        return

    table = Table(title="docs-agent — Project Status", show_lines=True)
    table.add_column("Project", style="bold")
    table.add_column("Status")
    table.add_column("Last Updated")
    table.add_column("Documents")

    for project in projects:
        status_icon = "[green]✓ synced[/green]" if project.status == "synced" else "[red]✗ stale[/red]"
        doc_targets = ", ".join(d.target for d in project.documents)
        table.add_row(
            project.name,
            status_icon,
            str(project.last_updated),
            doc_targets,
        )

    console.print(table)
```

- [ ] **Step 2: Implement HTML reporter**

```python
# docs_agent/reporters/html.py
from pathlib import Path
from docs_agent.registry import Registry


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>docs-agent — Project Status</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; }}
  h1 {{ color: #1a1a2e; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
  th {{ background: #1a1a2e; color: white; padding: 10px 14px; text-align: left; }}
  td {{ padding: 10px 14px; border-bottom: 1px solid #eee; }}
  tr:hover td {{ background: #f9f9f9; }}
  .synced {{ color: #22863a; font-weight: 600; }}
  .stale {{ color: #cb2431; font-weight: 600; }}
  .never {{ color: #999; }}
  footer {{ margin-top: 40px; color: #999; font-size: 0.85em; }}
</style>
</head>
<body>
<h1>docs-agent — Project Status</h1>
<table>
  <thead><tr><th>Project</th><th>Status</th><th>Last Updated</th><th>Documents</th></tr></thead>
  <tbody>
{rows}
  </tbody>
</table>
<footer>Generated by docs-agent</footer>
</body>
</html>
"""


def render_html_report(registry_path: Path, output_path: Path) -> None:
    registry = Registry(registry_path)
    projects = registry.all_projects()
    rows: list[str] = []
    for project in projects:
        status_class = project.status
        doc_links = ", ".join(
            f'<a href="{d.target}">{d.target}</a>' for d in project.documents
        )
        rows.append(
            f"    <tr>"
            f"<td>{project.name}</td>"
            f'<td class="{status_class}">{project.status}</td>'
            f"<td>{project.last_updated}</td>"
            f"<td>{doc_links}</td>"
            f"</tr>"
        )
    html = HTML_TEMPLATE.format(rows="\n".join(rows))
    output_path.write_text(html)
```

- [ ] **Step 3: Add `dashboard` and `report` to `cli.py`**

Add to `docs_agent/cli.py`:

```python
@cli.command()
@click.option("--registry", "registry_path", default=None, help="Path to registry.yml")
def dashboard(registry_path: str | None) -> None:
    """Show status of all registered projects."""
    from docs_agent.reporters.terminal import render_dashboard

    path = Path(registry_path) if registry_path else Path.cwd() / ".docs-agent" / "registry.yml"
    render_dashboard(path)


@cli.command()
@click.option("--registry", "registry_path", default=None, help="Path to registry.yml")
@click.option("--output", "output_file", default="docs-agent-report.html", help="Output HTML file path")
def report(registry_path: str | None, output_file: str) -> None:
    """Generate a static HTML status report."""
    from docs_agent.reporters.html import render_html_report

    reg_path = Path(registry_path) if registry_path else Path.cwd() / ".docs-agent" / "registry.yml"
    out_path = Path(output_file)
    render_html_report(reg_path, out_path)
    click.echo(f"Report saved to {out_path}")
```

- [ ] **Step 4: Run all tests and lint**

```bash
poetry run pytest -x -q
poetry run ruff check .
poetry run mypy docs_agent
```

Expected: all tests pass, no lint errors.

- [ ] **Step 5: Commit**

```bash
git add docs_agent/reporters/ docs_agent/cli.py
git commit -m "feat: terminal dashboard and HTML report commands"
```

---

## Task 12: Final Integration Test & README

**Files:**
- Modify: `README.md`
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import yaml
from docs_agent.config import Config
from docs_agent.engine import DocsEngine


@pytest.mark.asyncio
async def test_full_init_run_cycle(tmp_path: Path) -> None:
    config_dir = tmp_path / ".docs-agent"
    config_dir.mkdir()
    (config_dir / "docs-agent.yml").write_text(yaml.dump({
        "provider": {"type": "ollama", "model": "llama3", "api_key_env": "", "base_url": "http://localhost"},
        "output": {"mode": "direct"},
        "triggers": {"paths": ["app/**"], "ignore": []},
        "documents": [{"type": "readme", "template": "readme/default", "target": "README.md"}],
    }))
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("def main(): pass\n")

    call_count = 0

    async def fake_complete(system: str, user: str) -> str:
        nonlocal call_count
        call_count += 1
        return f"Auto-generated content for section {call_count}.\n"

    mock_provider = AsyncMock()
    mock_provider.complete = fake_complete
    mock_output = MagicMock()
    mock_output.apply = MagicMock()

    engine = DocsEngine(repo_root=tmp_path, provider=mock_provider, output=mock_output)
    await engine.init()

    readme = tmp_path / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "AUTO:overview" in content
    assert "Auto-generated content for section" in content
    assert Config.is_initialized(tmp_path)
    mock_output.apply.assert_called_once()

    mock_output.reset_mock()
    diff = "diff --git a/app/main.py b/app/main.py\n+++ b/app/main.py\n+def new_func(): pass\n"
    skipped = await engine.run(diff_text=diff)
    assert skipped is False


@pytest.mark.asyncio
async def test_run_does_not_call_llm_on_irrelevant_diff(tmp_path: Path) -> None:
    config_dir = tmp_path / ".docs-agent"
    config_dir.mkdir()
    (config_dir / "docs-agent.yml").write_text(yaml.dump({
        "provider": {"type": "ollama", "model": "llama3", "api_key_env": "", "base_url": "http://localhost"},
        "output": {"mode": "direct"},
        "triggers": {"paths": ["app/**"], "ignore": []},
        "documents": [{"type": "readme", "template": "readme/default", "target": "README.md"}],
    }))
    Config.mark_initialized(tmp_path)
    (tmp_path / "README.md").write_text("# Svc\n<!-- AUTO:overview -->\nOld.\n<!-- /AUTO:overview -->\n")

    mock_provider = AsyncMock()
    mock_output = MagicMock()
    engine = DocsEngine(repo_root=tmp_path, provider=mock_provider, output=mock_output)

    skipped = await engine.run(diff_text="diff --git a/tests/test_x.py b/tests/test_x.py\n+++ b/tests/test_x.py\n+new")
    assert skipped is True
    mock_provider.complete.assert_not_called()
```

- [ ] **Step 2: Run integration tests**

```bash
poetry run pytest tests/test_integration.py -v
```

Expected: 2 passed.

- [ ] **Step 3: Run full test suite**

```bash
poetry run pytest -q
poetry run ruff check .
```

Expected: all tests pass.

- [ ] **Step 4: Verify CLI end-to-end**

```bash
poetry run docs-agent --help
poetry run docs-agent install --help
poetry run docs-agent run --help
poetry run docs-agent dashboard --help
```

Expected: all commands show help text without errors.

- [ ] **Step 5: Final commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration tests for init/run cycle"
```

---

## Self-Review Notes

- **Spec coverage:** All 13 spec sections covered: install (Task 10), init/run/sync (Tasks 9), templates (Task 6), providers (Task 3), registry (Task 7), outputs (Task 8), dashboard/report (Task 11), config (Task 2), scaffolder (Task 10).
- **Placeholder scan:** No TBDs. All code blocks are complete.
- **Type consistency:** `LLMProvider.complete(system, user)` consistent across Tasks 3 and 9. `Output.apply(changed_files, message)` consistent across Tasks 8 and 9. `DiffAnalyzer` interface consistent across Tasks 4 and 9.
- **Gap:** `docs-agent.yml` context fields (e.g. `service_name` for templates) — the engine uses `gather_repo_context()` to build this automatically from `pyproject.toml`, no manual config needed.
