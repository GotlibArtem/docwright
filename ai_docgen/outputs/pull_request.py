from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path

import httpx

from ai_docgen.config import OutputConfig
from ai_docgen.outputs.base import Output


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
        remote_url = (
            subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=self.repo_root)
            .decode()
            .strip()
        )
        owner_repo = self.extract_owner_repo(remote_url)
        if not owner_repo:
            return
        default_branch = (
            subprocess.check_output(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=self.repo_root,
            )
            .decode()
            .strip()
            .replace("refs/remotes/origin/", "")
        )
        httpx.post(
            f"https://api.github.com/repos/{owner_repo}/pulls",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={
                "title": self.config.pr_title,
                "head": branch,
                "base": default_branch,
                "body": title,
            },
        )

    def extract_owner_repo(self, remote_url: str) -> str | None:
        match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", remote_url)
        return match.group(1) if match else None
