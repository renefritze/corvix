"""Command line interface for Corvix."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from os import environ
from pathlib import Path
from typing import TypeVar

import click
from rich.console import Console

from corvix.config import AppConfig, GitHubAccountConfig, PollingConfig, load_config, write_default_config
from corvix.domain import parse_timestamp
from corvix.env import get_env_value
from corvix.ingestion import GitHubNotificationsClient
from corvix.notifications.targets.base import NotificationTarget
from corvix.notifications.targets.slack import SlackTarget
from corvix.observability import configure_logging, setup_tracing
from corvix.services import (
    NotificationsClient,
    PollCycleInput,
    render_cached_dashboards,
    run_poll_cycle,
    run_watch_loop,
)
from corvix.storage import (
    StorageBackend,
    StorageConfigError,
    create_storage,
)
from corvix.web.app import run as run_web

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., object])


def _parse_bool_value(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    msg = f"Invalid boolean value: {value!r}"
    raise ValueError(msg)


def _resolve_apply_actions_default() -> bool | None:
    raw = get_env_value("CORVIX_DRY_RUN")
    if raw is None or not raw.strip():
        return None
    return not _parse_bool_value(raw)


def _apply_actions_callback(ctx: click.Context, param: click.Parameter, value: bool) -> bool:
    param_name = param.name
    if not param_name:
        return value
    if ctx.get_parameter_source(param_name) is click.core.ParameterSource.DEFAULT:
        try:
            resolved = _resolve_apply_actions_default()
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        if resolved is not None:
            return resolved
    return value


def _apply_actions_option() -> Callable[[F], F]:
    return click.option(
        "--apply-actions/--dry-run",
        default=True,
        show_default=True,
        callback=_apply_actions_callback,
        help=(
            "Apply mark-read actions to GitHub or only report planned actions. "
            "Set CORVIX_DRY_RUN=true to default to dry-run."
        ),
    )


@click.group(invoke_without_command=True)
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path, dir_okay=False, file_okay=True),
    default=Path("corvix.yaml"),
    show_default=True,
)
@click.pass_context
def main(ctx: click.Context, config_path: Path) -> None:
    """Corvix local GitHub notifications dashboard."""
    configure_logging()
    setup_tracing(service_name="corvix-poller")
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command("init-config")
@click.argument(
    "path",
    type=click.Path(path_type=Path, dir_okay=False, file_okay=True),
    default=Path("corvix.yaml"),
    required=False,
)
@click.option("--force", is_flag=True, default=False, help="Overwrite existing config file.")
def init_config_command(path: Path, force: bool) -> None:
    """Write a starter YAML config."""
    if path.exists() and not force:
        msg = f"Config already exists at '{path}'. Use --force to overwrite."
        raise click.ClickException(msg)
    write_default_config(path)
    click.echo(f"Wrote config to {path}")


@main.command("poll")
@_apply_actions_option()
@click.pass_context
def poll_command(ctx: click.Context, apply_actions: bool) -> None:
    """Run one poll cycle and persist processed notifications to cache."""
    config_path = _config_path_from_context(ctx)
    app_config = _load_app_config(config_path)
    clients = _build_clients(app_config.github.accounts, app_config.polling)
    targets = _build_targets(app_config)
    with _build_storage(app_config) as cache:
        summary = run_poll_cycle(
            PollCycleInput(
                config=app_config,
                clients=clients,
                cache=cache,
                apply_actions=apply_actions,
                notification_targets=targets,
            )
        )
    click.echo(f"Fetched: {summary.fetched}")
    click.echo(f"Excluded from dashboards: {summary.excluded}")
    click.echo(f"Actions executed: {summary.actions_taken}")
    for error in summary.errors:
        click.echo(f"Action error: {error}")


@main.command("watch")
@_apply_actions_option()
@click.option(
    "--iterations",
    type=click.IntRange(min=1),
    default=None,
    help="Number of polling iterations to run. Omit to run forever.",
)
@click.pass_context
def watch_command(ctx: click.Context, apply_actions: bool, iterations: int | None) -> None:
    """Run periodic poll cycles, suitable for cron-like local daemon behavior."""
    config_path = _config_path_from_context(ctx)
    app_config = _load_app_config(config_path)
    clients = _build_clients(app_config.github.accounts, app_config.polling)
    targets = _build_targets(app_config)
    with _build_storage(app_config) as cache:
        summaries = run_watch_loop(
            PollCycleInput(
                config=app_config,
                clients=clients,
                cache=cache,
                apply_actions=apply_actions,
                notification_targets=targets,
            ),
            iterations=iterations,
        )
    for index, summary in enumerate(summaries, start=1):
        click.echo(
            f"Run {index}: fetched={summary.fetched}, excluded={summary.excluded}, actions={summary.actions_taken}",
        )
        for error in summary.errors:
            click.echo(f"Action error: {error}")


@main.command("dashboard")
@click.option("--name", "dashboard_name", default=None, help="Render only one named dashboard.")
@click.pass_context
def dashboard_command(ctx: click.Context, dashboard_name: str | None) -> None:
    """Render dashboards from the persisted cache file without polling GitHub."""
    config_path = _config_path_from_context(ctx)
    app_config = _load_app_config(config_path)
    console = Console()
    with _build_storage(app_config) as cache:
        results = render_cached_dashboards(
            config=app_config,
            cache=cache,
            console=console,
            dashboard_name=dashboard_name,
        )
    if not results:
        click.echo("No dashboards rendered.")
        return
    for result in results:
        click.echo(f"{result.dashboard_name}: {result.rows} rows")


@main.command("serve")
@click.option("--host", default="0.0.0.0", show_default=True)  # nosec B104 - intentional server default; users pass 127.0.0.1 for local-only
@click.option("--port", default=8000, show_default=True, type=click.IntRange(min=1, max=65535))
@click.option("--reload/--no-reload", default=False, show_default=True)
@click.pass_context
def serve_command(ctx: click.Context, host: str, port: int, reload: bool) -> None:
    """Run Litestar dashboard website."""
    config_path = _config_path_from_context(ctx)
    environ["CORVIX_CONFIG"] = str(config_path)
    environ["CORVIX_WEB_HOST"] = host
    environ["CORVIX_WEB_PORT"] = str(port)
    environ["CORVIX_WEB_RELOAD"] = "true" if reload else "false"

    run_web()


@main.command("poller-health")
@click.pass_context
def poller_health_command(ctx: click.Context) -> None:
    """Exit 0 when the poller status in PostgreSQL is fresh, else fail.

    Intended for container healthchecks: it reads the poller status the watch
    loop writes to PostgreSQL and verifies a successful poll happened recently.
    """
    config_path = _config_path_from_context(ctx)
    app_config = _load_app_config(config_path)
    with _build_storage(app_config) as storage:
        status = storage.load_status()
    if status.status == "error":
        msg = f"Poller reported an error: {status.last_error}"
        raise click.ClickException(msg)
    if not status.last_poll_time:
        msg = "Poller has not recorded a successful poll yet."
        raise click.ClickException(msg)
    try:
        last_poll = parse_timestamp(status.last_poll_time)
    except ValueError as error:
        msg = f"Poller status has an invalid last poll time: {status.last_poll_time!r}"
        raise click.ClickException(msg) from error
    age = datetime.now(tz=UTC) - last_poll
    # Allow two poll cycles (with a 5-minute floor) before flagging staleness so a
    # single delayed cycle or a longer configured interval doesn't trip the check.
    threshold_seconds = max(300, app_config.polling.interval_seconds * 2)
    if age > timedelta(seconds=threshold_seconds):
        msg = (
            f"Poller is stale: {int(age.total_seconds())}s since last successful poll "
            f"(threshold: {threshold_seconds}s)."
        )
        raise click.ClickException(msg)
    click.echo("ok")


def _build_storage(app_config: AppConfig) -> StorageBackend:
    """Build the configured storage backend, surfacing config errors to the CLI."""
    try:
        return create_storage(app_config)
    except StorageConfigError as error:
        raise click.ClickException(str(error)) from error


def _load_app_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        msg = f"Config file '{config_path}' does not exist. Run `corvix init-config` first."
        raise click.ClickException(msg)
    try:
        return load_config(config_path)
    except ValueError as error:
        msg = f"Invalid config at '{config_path}': {error}"
        raise click.ClickException(msg) from error


def _resolve_token(token_env: str) -> str:
    try:
        token = get_env_value(token_env)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    if token:
        return token
    msg = f"Environment variable '{token_env}' (or '{token_env}_FILE') is required for polling GitHub notifications."
    raise click.ClickException(msg)


def _build_targets(app_config: AppConfig) -> list[NotificationTarget]:
    """Construct the server-side notification dispatch targets from config.

    Only server-side delivery channels are built here. Browser-tab and Web Push
    delivery are handled client-side by the web UI (from the ``browser_tab`` /
    ``web_push`` config echoed in the snapshot), so they are intentionally not
    represented as Python targets.

    A target whose secret env var is missing is skipped with a warning rather
    than silently doing nothing. When notification dispatch is enabled but no
    server-side target ends up configured, a note is logged so the "enabled but
    nothing happens" case is not silent.
    """
    notifications = app_config.notifications
    if not notifications.enabled:
        return []

    targets: list[NotificationTarget] = []

    slack_cfg = notifications.slack
    if slack_cfg.enabled:
        webhook_url = _resolve_optional_secret(slack_cfg.webhook_url_env)
        if webhook_url:
            targets.append(SlackTarget(webhook_url=webhook_url))
        else:
            logger.warning(
                "Slack notifications enabled but '%s' (or '%s_FILE') is not set; skipping Slack delivery.",
                slack_cfg.webhook_url_env,
                slack_cfg.webhook_url_env,
            )

    if not targets:
        logger.info(
            "Notification dispatch is enabled but no server-side targets are configured; "
            "browser-tab delivery, if enabled, is handled by the web UI."
        )
    return targets


def _resolve_optional_secret(env_var: str) -> str | None:
    """Resolve a secret env var (supporting ``<VAR>_FILE``), returning None if unset."""
    try:
        value = get_env_value(env_var)
    except ValueError:
        return None
    return value or None


def _build_clients(accounts: list[GitHubAccountConfig], polling: PollingConfig) -> tuple[NotificationsClient, ...]:
    clients: list[NotificationsClient] = []
    for account in accounts:
        token = _resolve_token(account.token_env)
        clients.append(
            GitHubNotificationsClient(
                token=token,
                api_base_url=account.api_base_url,
                account_id=account.id,
                account_label=account.label,
                request_timeout_seconds=polling.request_timeout_seconds,
            )
        )
    return tuple(clients)


def _config_path_from_context(ctx: click.Context) -> Path:
    config_path = ctx.obj.get("config_path") if ctx.obj else None
    if isinstance(config_path, Path):
        return config_path
    msg = "Missing config path in CLI context."
    raise click.ClickException(msg)
