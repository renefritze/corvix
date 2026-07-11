"""Prefilled ignore-rule snippet generation for a notification.

Backs the ``GET /api/v1/notifications/{account_id}/{thread_id}/rule-snippets``
route: given a stored notification record, it renders ready-to-paste YAML
snippets for dashboard-scoped ignores and global excludes, optionally including
enrichment-context predicates.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Literal, cast, overload

from litestar.exceptions import HTTPException

from corvix.domain import NotificationRecord
from corvix.web.actions import _require_account
from corvix.web.runtime_config import _load_runtime_config, _select_dashboard
from corvix.web.schemas import RuleSnippetsResponse
from corvix.web.storage_provider import _get_storage


def _notification_rule_snippets_impl(
    account_id: str,
    thread_id: str,
    dashboard: str | None = None,
) -> RuleSnippetsResponse:
    """Compute and return the typed rule-snippets payload."""
    config = _load_runtime_config()
    selected_dashboard = _select_dashboard(config.dashboards, dashboard)
    _require_account(config=config, account_id=account_id)
    _generated_at, records = _get_storage().load_records()
    record = _find_record(records=records, account_id=account_id, thread_id=thread_id)
    if record is None:
        msg = f"Notification '{account_id}/{thread_id}' not found in storage."
        raise HTTPException(status_code=404, detail=msg)
    base_match = _rule_match_lines(record=record, include_context=False)
    context_match = _rule_match_lines(record=record, include_context=True)
    return RuleSnippetsResponse(
        dashboard_name=selected_dashboard.name,
        dashboard_ignore_rule_snippet=_dashboard_ignore_rule_snippet(base_match),
        global_exclude_rule_snippet=_global_exclude_rule_snippet(record=record, match_lines=base_match),
        dashboard_ignore_rule_with_context_snippet=(
            _dashboard_ignore_rule_snippet(context_match) if context_match is not None else None
        ),
        global_exclude_rule_with_context_snippet=(
            _global_exclude_rule_snippet(record=record, match_lines=context_match)
            if context_match is not None
            else None
        ),
        has_context=bool(record.context),
    )


def _find_record(
    *,
    records: list[NotificationRecord],
    account_id: str,
    thread_id: str,
) -> NotificationRecord | None:
    for record in records:
        if record.notification.account_id == account_id and record.notification.thread_id == thread_id:
            return record
    return None


def _yaml_quoted(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_scalar(value: object) -> str:
    if isinstance(value, str):
        return _yaml_quoted(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _slug_token(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "rule"


def _rule_name_for_record(record: NotificationRecord) -> str:
    notification = record.notification
    repository = notification.repository
    reason = notification.reason
    subject_type = notification.subject_type
    return f"ignore-{_slug_token(repository)}-{_slug_token(reason)}-{_slug_token(subject_type)}"


@overload
def _rule_match_lines(*, record: NotificationRecord, include_context: Literal[False]) -> list[str]: ...


@overload
def _rule_match_lines(*, record: NotificationRecord, include_context: Literal[True]) -> list[str] | None: ...


def _rule_match_lines(*, record: NotificationRecord, include_context: bool) -> list[str] | None:
    notification = record.notification
    repository = notification.repository
    reason = notification.reason
    subject_type = notification.subject_type
    title_regex = _anchored_title_regex(notification.subject_title)
    lines = [
        f"repository_in: [{_yaml_quoted(repository)}]",
        f"reason_in: [{_yaml_quoted(reason)}]",
        f"subject_type_in: [{_yaml_quoted(subject_type)}]",
        f"title_regex: {_yaml_quoted(title_regex)}",
    ]
    if not include_context:
        return lines
    context_predicates = _context_predicate_lines(record=record)
    if not context_predicates:
        return None
    return [*lines, "context:", *context_predicates]


def _context_predicate_lines(*, record: NotificationRecord) -> list[str]:
    context = record.context
    candidate_paths = (
        "github.latest_comment.is_ci_only",
        "github.pr_state.state",
        "github.pr_state.draft",
    )
    output: list[str] = []
    for path in candidate_paths:
        found, value = _context_path_value(context=context, path=path)
        if not found:
            continue
        if isinstance(value, bool | int | float | str):
            output.extend(
                [
                    f"  - path: {_yaml_quoted(path)}",
                    "    op: equals",
                    f"    value: {_yaml_scalar(value)}",
                ]
            )
    return output


def _anchored_title_regex(title: str) -> str:
    escaped = re.sub(r"([.^$*+?{}\[\]|()\\])", r"\\\1", title)
    return f"^{escaped}$"


def _context_path_value(*, context: Mapping[str, object], path: str) -> tuple[bool, object | None]:
    current: object = context
    for segment in path.split("."):
        if not isinstance(current, dict):
            return False, None
        current_map = cast(dict[str, object], current)
        next_value = current_map.get(segment)
        if next_value is None and segment not in current_map:
            return False, None
        current = next_value
    return True, current


def _dashboard_ignore_rule_snippet(match_lines: list[str]) -> str:
    body = "\n".join(f"  {line}" for line in match_lines)
    return f"- {body.lstrip()}"


def _global_exclude_rule_snippet(*, record: NotificationRecord, match_lines: list[str]) -> str:
    match_body = "\n".join(f"    {line}" for line in match_lines)
    return f"- name: {_rule_name_for_record(record)}\n  match:\n{match_body}\n  exclude_from_dashboards: true"
