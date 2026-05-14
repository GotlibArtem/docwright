from pathlib import Path

from docwright.config import OutputConfig
from docwright.outputs.base import Output
from docwright.outputs.direct import DirectOutput
from docwright.outputs.pull_request import PullRequestOutput


def build_output(config: OutputConfig, repo_root: Path) -> Output:
    if config.mode == "direct":
        return DirectOutput(repo_root=repo_root)
    return PullRequestOutput(repo_root=repo_root, config=config)
