from pathlib import Path

import pytest


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A temporary directory simulating a repo root."""
    return tmp_path
