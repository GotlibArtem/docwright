from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import click

from ai_docgen.config import Config
from ai_docgen.engine import DocsEngine
from ai_docgen.outputs.factory import build_output
from ai_docgen.providers.factory import build_provider


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
    base_sha = os.environ.get("AI_DOCGEN_BASE_SHA", "HEAD~1")
    try:
        diff_text = subprocess.check_output(
            ["git", "diff", f"{base_sha}..HEAD"], cwd=repo_root
        ).decode()
    except subprocess.CalledProcessError:
        diff_text = ""
    if dry_run:
        config = Config.load(repo_root)
        triggers = config.triggers
        from ai_docgen.analyzer import DiffAnalyzer

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


@cli.command("install")
@click.option("--auto", is_flag=True, help="Non-interactive mode with auto-detected defaults.")
@click.option("--provider", default=None, type=click.Choice(["claude", "openai", "ollama"]))
@click.option("--output", "output_mode", default=None, type=click.Choice(["pr", "direct"]))
def install(auto: bool, provider: str | None, output_mode: str | None) -> None:
    """Bootstrap this repo with ai-docgen configuration."""
    from ai_docgen.scaffolder import Scaffolder

    repo_root = get_repo_root()
    scaffolder = Scaffolder(repo_root=repo_root)
    profile = scaffolder.detect_profile()

    if auto:
        final_provider = provider or "claude"
        final_output = output_mode or "pr"
    else:
        click.echo(
            f"Detected: {profile.language} project '{profile.service_name}', CI: {profile.ci}"
        )
        final_provider = provider or click.prompt(
            "LLM provider",
            type=click.Choice(["claude", "openai", "ollama"]),
            default="claude",
        )
        final_output = output_mode or click.prompt(
            "Output mode",
            type=click.Choice(["pr", "direct"]),
            default="pr",
        )

    scaffolder.generate(profile, provider_type=final_provider, output_mode=final_output)
    click.echo(f"Installed ai-docgen for '{profile.service_name}'.")
    click.echo("Next: set your API key env var, then run 'make docs'.")


@cli.command()
@click.option("--registry", "registry_path", default=None, help="Path to registry.yml")
def dashboard(registry_path: str | None) -> None:
    """Show status of all registered projects."""
    from ai_docgen.reporters.terminal import render_dashboard

    path = Path(registry_path) if registry_path else Path.cwd() / ".ai-docgen" / "registry.yml"
    render_dashboard(path)


@cli.command()
@click.option("--registry", "registry_path", default=None, help="Path to registry.yml")
@click.option("--output", "output_file", default="ai-docgen-report.html", help="Output HTML file")
def report(registry_path: str | None, output_file: str) -> None:
    """Generate a static HTML status report."""
    from ai_docgen.reporters.html import render_html_report

    reg_path = Path(registry_path) if registry_path else Path.cwd() / ".ai-docgen" / "registry.yml"
    render_html_report(reg_path, Path(output_file))
    click.echo(f"Report saved to {output_file}")
