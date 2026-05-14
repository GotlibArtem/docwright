from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import click

from docs_agent.config import Config
from docs_agent.engine import DocsEngine
from docs_agent.outputs.factory import build_output
from docs_agent.providers.factory import build_provider


def get_repo_root() -> Path:
    return Path.cwd()


def build_engine(repo_root: Path) -> DocsEngine:
    config = Config.load(repo_root)
    provider = build_provider(config.provider)
    output = build_output(config.output, repo_root)
    return DocsEngine(repo_root=repo_root, provider=provider, output=output)


@click.group()
def cli() -> None:
    """AI-powered documentation agent."""


@cli.command()
def init() -> None:
    """Generate documentation from scratch."""
    engine = build_engine(get_repo_root())
    asyncio.run(engine.init())
    click.echo("Documentation initialized.")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Show what would change without writing files.")
def run(dry_run: bool) -> None:
    """Incrementally update documentation based on recent git diff."""
    repo_root = get_repo_root()
    base_sha = os.environ.get("DOCS_AGENT_BASE_SHA", "HEAD~1")
    try:
        diff_text = subprocess.check_output(
            ["git", "diff", f"{base_sha}..HEAD"], cwd=repo_root
        ).decode()
    except subprocess.CalledProcessError:
        diff_text = ""
    if dry_run:
        config = Config.load(repo_root)
        triggers = config.triggers
        from docs_agent.analyzer import DiffAnalyzer

        analyzer = DiffAnalyzer(
            diff_text=diff_text,
            trigger_paths=triggers.paths if triggers else [],
            ignore_paths=triggers.ignore if triggers else [],
        )
        if analyzer.has_relevant_changes():
            click.echo("Relevant changes detected — documentation would be updated.")
        else:
            click.echo("No relevant changes — documentation would be skipped.")
        return
    engine = build_engine(repo_root)
    skipped = asyncio.run(engine.run(diff_text=diff_text))
    click.echo(
        "No relevant changes — documentation up to date." if skipped else "Documentation updated."
    )


@cli.command()
def sync() -> None:
    """Force re-sync all documentation against current templates."""
    engine = build_engine(get_repo_root())
    asyncio.run(engine.sync())
    click.echo("Documentation synced.")
