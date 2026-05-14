from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

CONFIG_DIR = ".ai-docgen"
CONFIG_FILE = "ai-docgen.yml"
INITIALIZED_MARKER = ".initialized"


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
    local_path: str = ".ai-docgen/templates"


class TriggersConfig(BaseModel):
    paths: list[str] = Field(default_factory=lambda: ["app/**", "src/**"])
    ignore: list[str] = Field(default_factory=lambda: ["tests/**", "**/*.md"])


class DocumentConfig(BaseModel):
    type: Literal["readme", "wiki"]
    template: str
    target: str


class RegistryConfig(BaseModel):
    path: str = "../.ai-docgen/registry.yml"


class Config(BaseModel):
    provider: ProviderConfig
    output: OutputConfig = Field(default_factory=OutputConfig)
    templates: TemplatesConfig = Field(default_factory=TemplatesConfig)
    triggers: TriggersConfig | None = None
    documents: list[DocumentConfig] = Field(default_factory=list)
    registry: RegistryConfig = Field(default_factory=RegistryConfig)

    @classmethod
    def load(cls, repo_root: Path) -> Config:
        config_path = repo_root / CONFIG_DIR / CONFIG_FILE
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
        data = yaml.safe_load(config_path.read_text())
        return cls.model_validate(data)

    @classmethod
    def is_initialized(cls, repo_root: Path) -> bool:
        return (repo_root / CONFIG_DIR / INITIALIZED_MARKER).exists()

    @classmethod
    def mark_initialized(cls, repo_root: Path) -> None:
        marker = repo_root / CONFIG_DIR / INITIALIZED_MARKER
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
