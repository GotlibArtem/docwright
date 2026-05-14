from pathlib import Path

from rich.console import Console
from rich.table import Table

from ai_docgen.registry import Registry


def render_dashboard(registry_path: Path) -> None:
    console = Console()
    registry = Registry(registry_path)
    projects = registry.all_projects()

    if not projects:
        console.print("[yellow]No projects registered. Run 'ai-docgen init' in a project.[/yellow]")
        return

    table = Table(title="ai-docgen — Project Status", show_lines=True)
    table.add_column("Project", style="bold")
    table.add_column("Status")
    table.add_column("Last Updated")
    table.add_column("Documents")

    for project in projects:
        status_icon = (
            "[green]✓ synced[/green]" if project.status == "synced" else "[red]✗ stale[/red]"
        )
        doc_targets = ", ".join(d.target for d in project.documents)
        table.add_row(project.name, status_icon, str(project.last_updated), doc_targets)

    console.print(table)
