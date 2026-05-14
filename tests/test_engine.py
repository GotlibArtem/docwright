from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from docwright.config import Config
from docwright.engine import DocsEngine


def make_config_file(tmp_path: Path) -> None:
    config_dir = tmp_path / ".ai-docgen"
    config_dir.mkdir(parents=True)
    (config_dir / "ai-docgen.yml").write_text(
        yaml.dump(
            {
                "provider": {
                    "type": "ollama",
                    "model": "llama3",
                    "api_key_env": "",
                    "base_url": "http://localhost:11434",
                },
                "output": {"mode": "direct"},
                "triggers": {"paths": ["app/**"], "ignore": []},
                "documents": [
                    {"type": "readme", "template": "readme/default", "target": "README.md"}
                ],
            }
        )
    )


@pytest.mark.asyncio
async def test_init_creates_readme_when_missing(tmp_path: Path) -> None:
    make_config_file(tmp_path)
    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(return_value="Generated overview.\n")
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
    (tmp_path / "README.md").write_text(
        "# Existing\n<!-- AUTO:overview -->\nOld.\n<!-- /AUTO:overview -->\n"
    )
    Config.mark_initialized(tmp_path)

    mock_provider = AsyncMock()
    mock_output = MagicMock()

    engine = DocsEngine(repo_root=tmp_path, provider=mock_provider, output=mock_output)
    diff = "diff --git a/tests/test_foo.py b/tests/test_foo.py\n+++ b/tests/test_foo.py\n+new line"
    skipped = await engine.run(diff_text=diff)

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
