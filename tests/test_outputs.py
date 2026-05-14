from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docs_agent.config import OutputConfig
from docs_agent.outputs.base import Output
from docs_agent.outputs.direct import DirectOutput
from docs_agent.outputs.factory import build_output
from docs_agent.outputs.pull_request import PullRequestOutput


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
