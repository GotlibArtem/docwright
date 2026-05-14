from abc import ABC, abstractmethod
from pathlib import Path


class Output(ABC):
    @abstractmethod
    def apply(self, changed_files: list[Path], message: str) -> None: ...
