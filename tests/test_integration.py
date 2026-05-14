from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from ai_docgen.config import Config
from ai_docgen.engine import DocsEngine


def make_full_config(tmp_path: Path) -> None:
    config_dir = tmp_path / ".ai-docgen"
    config_dir.mkdir()
    (config_dir / "ai-docgen.yml").write_text(
        yaml.dump(
            {
                "provider": {
                    "type": "ollama",
                    "model": "llama3",
                    "api_key_env": "",
                    "base_url": "http://localhost",
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
async def test_full_init_run_cycle(tmp_path: Path) -> None:
    make_full_config(tmp_path)
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
    make_full_config(tmp_path)
    Config.mark_initialized(tmp_path)
    (tmp_path / "README.md").write_text(
        "# Svc\n<!-- AUTO:overview -->\nOld.\n<!-- /AUTO:overview -->\n"
    )

    mock_provider = AsyncMock()
    mock_output = MagicMock()
    engine = DocsEngine(repo_root=tmp_path, provider=mock_provider, output=mock_output)

    diff = "diff --git a/tests/test_x.py b/tests/test_x.py\n+++ b/tests/test_x.py\n+new\n"
    skipped = await engine.run(diff_text=diff)
    assert skipped is True
    mock_provider.complete.assert_not_called()
