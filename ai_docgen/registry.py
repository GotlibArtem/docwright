from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml

STALE_DAYS = 30


def _as_date(value: date | str | None, fallback: date) -> date:
    if value is None:
        return fallback
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _as_optional_date(value: date | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


@dataclass
class DocumentEntry:
    target: str
    last_updated: date | None = None


@dataclass
class ProjectEntry:
    name: str
    path: str
    remote: str
    documents: list[DocumentEntry] = field(default_factory=list)
    registered_at: date = field(default_factory=date.today)
    last_updated: date = field(default_factory=date.today)
    status: str = "synced"

    def compute_status(self) -> str:
        if (date.today() - self.last_updated) > timedelta(days=STALE_DAYS):
            return "stale"
        return "synced"


class Registry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def all_projects(self) -> list[ProjectEntry]:
        if not self.path.exists():
            return []
        data = yaml.safe_load(self.path.read_text()) or {}
        projects = []
        for p in data.get("projects", []):
            docs = [
                DocumentEntry(
                    target=d["target"],
                    last_updated=_as_optional_date(d.get("last_updated")),
                )
                for d in p.get("documents", [])
            ]
            projects.append(
                ProjectEntry(
                    name=p["name"],
                    path=p["path"],
                    remote=p.get("remote", ""),
                    documents=docs,
                    registered_at=_as_date(p.get("registered_at"), date.today()),
                    last_updated=_as_date(p.get("last_updated"), date.today()),
                    status=p.get("status", "synced"),
                )
            )
        return projects

    def register(self, entry: ProjectEntry) -> None:
        projects = self.all_projects()
        existing = next((p for p in projects if p.name == entry.name), None)
        if existing:
            projects.remove(existing)
        entry.last_updated = date.today()
        entry.status = entry.compute_status()
        projects.append(entry)
        self.write(projects)

    def update_document_timestamp(self, project_name: str, target: str, updated: date) -> None:
        projects = self.all_projects()
        for project in projects:
            if project.name == project_name:
                for doc in project.documents:
                    if doc.target == target:
                        doc.last_updated = updated
                project.last_updated = updated
                project.status = project.compute_status()
        self.write(projects)

    def write(self, projects: list[ProjectEntry]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "projects": [
                {
                    "name": p.name,
                    "path": p.path,
                    "remote": p.remote,
                    "registered_at": p.registered_at.isoformat(),
                    "last_updated": p.last_updated.isoformat(),
                    "status": p.status,
                    "documents": [
                        {
                            "target": d.target,
                            "last_updated": (
                                d.last_updated.isoformat() if d.last_updated else None
                            ),
                        }
                        for d in p.documents
                    ],
                }
                for p in projects
            ]
        }
        self.path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
