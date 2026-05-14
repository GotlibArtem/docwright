from pathlib import Path

from git import Repo

from ai_docgen.outputs.base import Output


class DirectOutput(Output):
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def apply(self, changed_files: list[Path], message: str) -> None:
        repo = Repo(self.repo_root)
        str_paths = [str(f.relative_to(self.repo_root)) for f in changed_files]
        repo.index.add(str_paths)
        repo.index.commit(message)
