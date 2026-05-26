"""Dashboard configuration model and YAML parsing."""

from __future__ import annotations

from dataclasses import dataclass, field

from corvix.config._utils import (
    _ensure_list,
    _ensure_map,
    _get_bool,
    _get_int,
    _get_str,
)
from corvix.config.rules import MatchCriteria, _parse_match

NO_FILTERS_DASHBOARD_NAME = "no filters"


@dataclass(slots=True)
class DashboardSpec:
    """Dashboard configuration for sorting, grouping, and filtering."""

    name: str
    group_by: str = "none"
    sort_by: str = "score"
    descending: bool = True
    include_read: bool = False
    max_items: int = 100
    match: MatchCriteria = field(default_factory=MatchCriteria)
    ignore_rules: list[MatchCriteria] = field(default_factory=list)


def default_dashboard() -> DashboardSpec:
    """Return the fallback dashboard used when config defines none."""
    return DashboardSpec(name="default", group_by="repository", sort_by="score")


def no_filters_dashboard() -> DashboardSpec:
    """Return the hardcoded dashboard that bypasses config-driven filtering."""
    return DashboardSpec(
        name=NO_FILTERS_DASHBOARD_NAME,
        group_by="repository",
        sort_by="score",
        descending=True,
        include_read=True,
        max_items=0,
    )


def available_dashboards(dashboards: list[DashboardSpec]) -> list[DashboardSpec]:
    """Return configured dashboards plus the built-in rule-free dashboard."""
    configured_dashboards = [dashboard for dashboard in dashboards if dashboard.name != NO_FILTERS_DASHBOARD_NAME]
    if configured_dashboards:
        return [*configured_dashboards, no_filters_dashboard()]
    if dashboards:
        return [no_filters_dashboard()]
    return [default_dashboard(), no_filters_dashboard()]


def is_no_filters_dashboard(dashboard: DashboardSpec) -> bool:
    """Return whether the dashboard is the hardcoded rule-free dashboard."""
    return dashboard.name == NO_FILTERS_DASHBOARD_NAME


def _parse_dashboards(value: object) -> list[DashboardSpec]:
    dashboards = _ensure_list(value, "dashboards")
    parsed: list[DashboardSpec] = []
    for raw_dashboard in dashboards:
        dashboard = _ensure_map(raw_dashboard, "dashboard entry")
        dashboard_name = _get_str(dashboard, "name", "default", "dashboards[].name")
        if dashboard_name == NO_FILTERS_DASHBOARD_NAME:
            msg = (
                f"Config field 'dashboards[].name' cannot be '{NO_FILTERS_DASHBOARD_NAME}' "
                "because that dashboard name is reserved."
            )
            raise ValueError(msg)
        parsed.append(
            DashboardSpec(
                name=dashboard_name,
                group_by=_get_str(dashboard, "group_by", "none", "dashboards[].group_by"),
                sort_by=_get_str(dashboard, "sort_by", "score", "dashboards[].sort_by"),
                descending=_get_bool(dashboard, "descending", True, "dashboards[].descending"),
                include_read=_get_bool(dashboard, "include_read", False, "dashboards[].include_read"),
                max_items=_get_int(dashboard, "max_items", 100, "dashboards[].max_items"),
                match=_parse_match(dashboard.get("match", {})),
                ignore_rules=_parse_dashboard_ignore_rules(dashboard.get("ignore_rules", [])),
            ),
        )
    return parsed


def _parse_dashboard_ignore_rules(value: object) -> list[MatchCriteria]:
    rules = _ensure_list(value, "dashboards[].ignore_rules")
    return [_parse_match(item, section="dashboards[].ignore_rules[]") for item in rules]
