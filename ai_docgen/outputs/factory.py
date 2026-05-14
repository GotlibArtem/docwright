from pathlib import Path

from ai_docgen.config import OutputConfig
from ai_docgen.outputs.base import Output
from ai_docgen.outputs.direct import DirectOutput
from ai_docgen.outputs.pull_request import PullRequestOutput


def build_output(config: OutputConfig, repo_root: Path) -> Output:
    if config.mode == "direct":
        return DirectOutput(repo_root=repo_root)
    return PullRequestOutput(repo_root=repo_root, config=config)
