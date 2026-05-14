from pathlib import Path

from docs_agent.config import OutputConfig
from docs_agent.outputs.base import Output
from docs_agent.outputs.direct import DirectOutput
from docs_agent.outputs.pull_request import PullRequestOutput


def build_output(config: OutputConfig, repo_root: Path) -> Output:
    if config.mode == "direct":
        return DirectOutput(repo_root=repo_root)
    return PullRequestOutput(repo_root=repo_root, config=config)
