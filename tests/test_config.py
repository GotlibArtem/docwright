from pathlib import Path

import pytest
import yaml

from docwright.config import Config


def test_load_minimal_config(tmp_path: Path) -> None:
    config_dir = tmp_path / ".ai-docgen"
    config_dir.mkdir()
    config_file = config_dir / "ai-docgen.yml"
    config_file.write_text(
        yaml.dump(
            {
                "provider": {
                    "type": "claude",
                    "model": "claude-sonnet-4-6",
                    "api_key_env": "ANTHROPIC_API_KEY",
                },
                "output": {"mode": "pr"},
                "documents": [
                    {"type": "readme", "template": "readme/default", "target": "README.md"}
                ],
            }
        )
    )
    config = Config.load(tmp_path)
    assert config.provider.type == "claude"
    assert config.output.mode == "pr"
    assert len(config.documents) == 1
    assert config.documents[0].target == "README.md"


def test_load_config_with_triggers(tmp_path: Path) -> None:
    config_dir = tmp_path / ".ai-docgen"
    config_dir.mkdir()
    config_file = config_dir / "ai-docgen.yml"
    config_file.write_text(
        yaml.dump(
            {
                "provider": {"type": "openai", "model": "gpt-4o", "api_key_env": "OPENAI_API_KEY"},
                "output": {"mode": "direct"},
                "triggers": {"paths": ["app/**"], "ignore": ["tests/**"]},
                "documents": [],
            }
        )
    )
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
