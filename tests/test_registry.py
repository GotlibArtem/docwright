from datetime import date
from pathlib import Path

from ai_docgen.registry import DocumentEntry, ProjectEntry, Registry


def test_register_new_project(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yml"
    registry = Registry(registry_path)
    registry.register(
        ProjectEntry(
            name="my-service",
            path="../my-service",
            remote="git@github.com:org/my-service.git",
            documents=[DocumentEntry(target="README.md")],
        )
    )
    loaded = Registry(registry_path)
    projects = loaded.all_projects()
    assert len(projects) == 1
    assert projects[0].name == "my-service"


def test_register_updates_existing_project(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yml"
    registry = Registry(registry_path)
    registry.register(
        ProjectEntry(
            name="my-service",
            path="../my-service",
            remote="git@github.com:org/my-service.git",
            documents=[DocumentEntry(target="README.md")],
        )
    )
    registry.register(
        ProjectEntry(
            name="my-service",
            path="../my-service",
            remote="git@github.com:org/my-service.git",
            documents=[
                DocumentEntry(target="README.md"),
                DocumentEntry(target="../wiki/architecture.md"),
            ],
        )
    )
    projects = Registry(registry_path).all_projects()
    assert len(projects) == 1
    assert len(projects[0].documents) == 2


def test_update_document_timestamp(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yml"
    registry = Registry(registry_path)
    registry.register(
        ProjectEntry(
            name="my-service",
            path="../my-service",
            remote="",
            documents=[DocumentEntry(target="README.md")],
        )
    )
    registry.update_document_timestamp("my-service", "README.md", date(2026, 5, 14))
    projects = Registry(registry_path).all_projects()
    doc = next(d for d in projects[0].documents if d.target == "README.md")
    assert doc.last_updated == date(2026, 5, 14)


def test_empty_registry_returns_empty_list(tmp_path: Path) -> None:
    registry = Registry(tmp_path / "registry.yml")
    assert registry.all_projects() == []
