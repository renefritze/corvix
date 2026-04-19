"""Rich dashboard rendering from persisted notification records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rich.console import Console
from rich.table import Table

from corvix.config import DashboardSpec
from corvix.dashboarding import build_dashboard_data
from corvix.domain import NotificationRecord


@dataclass(slots=True)
class DashboardRenderResult:
    """Rendered dashboard metadata."""

    dashboard_name: str
    rows: int


def render_dashboards(
    console: Console,
    records: list[NotificationRecord],
    dashboards: list[DashboardSpec],
    generated_at: datetime | None,
) -> list[DashboardRenderResult]:
    """Render one table per dashboard group."""
    results: list[DashboardRenderResult] = []
    if generated_at is not None:
        console.print(f"[bold]Snapshot:[/bold] {generated_at.isoformat()}")
    for dashboard in dashboards:
        data = build_dashboard_data(
            records=records,
            dashboard=dashboard,
            generated_at=generated_at,
        )
        row_count = 0
        for group in data.groups:
            table = _build_table(dashboard=dashboard, group_name=group.name)
            for item in group.items:
                row_count += 1
                table.add_row(
                    item.account_label,
                    f"{item.score:.2f}",
                    item.updated_at,
                    item.repository,
                    item.reason,
                    item.subject_type,
                    item.subject_title,
                    "yes" if item.unread else "no",
                    ", ".join(item.matched_rules),
                    ", ".join(item.actions_taken),
                )
            console.print(table)
        results.append(DashboardRenderResult(dashboard_name=dashboard.name, rows=row_count))
    return results


def _build_table(dashboard: DashboardSpec, group_name: str) -> Table:
    title = f"{dashboard.name} [{group_name}]"
    table = Table(title=title)
    table.add_column("Account")
    table.add_column("Score", justify="right")
    table.add_column("Updated")
    table.add_column("Repository")
    table.add_column("Reason")
    table.add_column("Type")
    table.add_column("Title")
    table.add_column("Unread")
    table.add_column("Rules")
    table.add_column("Actions")
    return table
