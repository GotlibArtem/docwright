import json
from pathlib import Path

from docwright.scaffolder import Scaffolder


def test_detect_python_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "my-service"\n')
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    assert profile.language == "python"
    assert profile.service_name == "my-service"


def test_detect_node_project(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"name": "my-frontend"}))
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    assert profile.language == "node"
    assert profile.service_name == "my-frontend"


def test_detect_github_actions_ci(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "svc"\n')
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    assert profile.ci == "github"


def test_detect_gitlab_ci(tmp_path: Path) -> None:
    (tmp_path / ".gitlab-ci.yml").touch()
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "svc"\n')
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    assert profile.ci == "gitlab"


def test_generate_creates_config_file(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "my-svc"\n')
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    scaffolder.generate(profile, provider_type="claude", output_mode="pr")
    config_file = tmp_path / ".ai-docgen" / "ai-docgen.yml"
    assert config_file.exists()
    assert "claude" in config_file.read_text()


def test_generate_adds_makefile_targets(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "svc"\n')
    makefile = tmp_path / "Makefile"
    makefile.write_text("test:\n\tpoetry run pytest\n")
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    scaffolder.generate(profile, provider_type="claude", output_mode="pr")
    content = makefile.read_text()
    assert "docs:" in content
    assert "docs-sync:" in content


def test_generate_github_actions_workflow(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "svc"\n')
    scaffolder = Scaffolder(repo_root=tmp_path)
    profile = scaffolder.detect_profile()
    scaffolder.generate(profile, provider_type="claude", output_mode="pr")
    workflow = tmp_path / ".github" / "workflows" / "docs.yml"
    assert workflow.exists()
    assert "ai-docgen run" in workflow.read_text()
