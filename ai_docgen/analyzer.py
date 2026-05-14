from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass


@dataclass
class ChangedFile:
    path: str


class DiffAnalyzer:
    def __init__(
        self,
        diff_text: str,
        trigger_paths: list[str],
        ignore_paths: list[str],
    ) -> None:
        self.diff_text = diff_text
        self.trigger_paths = trigger_paths
        self.ignore_paths = ignore_paths

    def changed_files(self) -> list[ChangedFile]:
        paths: list[str] = []
        for line in self.diff_text.splitlines():
            match = re.match(r"^\+\+\+ b/(.+)$", line)
            if match:
                paths.append(match.group(1))
        return [ChangedFile(path=p) for p in paths]

    def has_relevant_changes(self) -> bool:
        for changed in self.changed_files():
            if self.is_ignored(changed.path):
                continue
            if self.matches_trigger(changed.path):
                return True
        return False

    def diff_summary(self) -> str:
        files = self.changed_files()
        if not files:
            return "No changed files."
        lines = ["Changed files:"]
        for f in files:
            lines.append(f"  - {f.path}")
        lines.append("")
        lines.append(self.diff_text[:3000])
        if len(self.diff_text) > 3000:
            lines.append("... (truncated)")
        return "\n".join(lines)

    def is_ignored(self, path: str) -> bool:
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.ignore_paths)

    def matches_trigger(self, path: str) -> bool:
        if not self.trigger_paths:
            return True
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.trigger_paths)
