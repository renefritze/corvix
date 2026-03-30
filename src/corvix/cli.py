"""Command line interface for Corvix."""

from __future__ import annotations

from datetime import UTC, datetime
from os import environ
from pathlib import Path

import click
from rich.console import Console

from corvix.config import AppConfig, load_config, write_default_config
from corvix.db import get_database_url
from corvix.ingestion import GitHubNotificationsClient
from corvix.services import render_cached_dashboards, run_poll_cycle, run_watch_loop
from corvix.storage import NotificationCache, PostgresStorage
from corvix.web.app import run as run_web


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
@click.option(
    "--apply-actions/--dry-run",
    default=False,
    show_default=True,
    help="Apply mark-read actions to GitHub or only report planned actions.",
)
@click.pass_context
def poll_command(ctx: click.Context, apply_actions: bool) -> None:
    """Run one poll cycle and persist processed notifications to cache."""
    config_path = _config_path_from_context(ctx)
    app_config = _load_app_config(config_path)
    token = _resolve_token(app_config.github.token_env)
    client = GitHubNotificationsClient(token=token, api_base_url=app_config.github.api_base_url)
    cache = NotificationCache(path=app_config.resolve_cache_file())
    summary = run_poll_cycle(
        config=app_config,
        client=client,
        cache=cache,
        apply_actions=apply_actions,
    )
    click.echo(f"Fetched: {summary.fetched}")
    click.echo(f"Excluded from dashboards: {summary.excluded}")
    click.echo(f"Actions executed: {summary.actions_taken}")
    click.echo(f"Cache file: {cache.path}")
    for error in summary.errors:
        click.echo(f"Action error: {error}")


@main.command("watch")
@click.option(
    "--apply-actions/--dry-run",
    default=False,
    show_default=True,
    help="Apply mark-read actions to GitHub or only report planned actions.",
)
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
    token = _resolve_token(app_config.github.token_env)
    client = GitHubNotificationsClient(token=token, api_base_url=app_config.github.api_base_url)
    cache = NotificationCache(path=app_config.resolve_cache_file())
    summaries = run_watch_loop(
        config=app_config,
        client=client,
        cache=cache,
        apply_actions=apply_actions,
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
    cache = NotificationCache(path=app_config.resolve_cache_file())
    console = Console()
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
@click.option("--host", default="0.0.0.0", show_default=True)
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


@main.command("migrate-cache")
@click.option(
    "--user-id",
    required=True,
    help="UUID of the user to assign imported records to.",
)
@click.pass_context
def migrate_cache_command(ctx: click.Context, user_id: str) -> None:
    """Import JSON cache records into PostgreSQL for a given user.

    Reads the cache file from the config, then upserts all records into the
    PostgreSQL database using the DATABASE_URL (or the env var named in
    config.database.url_env).
    """
    config_path = _config_path_from_context(ctx)
    app_config = _load_app_config(config_path)
    db_url = get_database_url(app_config.database.url_env)
    if not db_url:
        msg = f"Environment variable '{app_config.database.url_env}' is not set."
        raise click.ClickException(msg)

    cache = NotificationCache(path=app_config.resolve_cache_file())
    generated_at, records = cache.load()
    if not records:
        click.echo("Cache is empty or not found — nothing to migrate.")
        return

    snapshot_time = generated_at if generated_at is not None else datetime.now(tz=UTC)
    storage = PostgresStorage(connection_string=db_url)
    storage.save_records(user_id=user_id, records=records, generated_at=snapshot_time)
    click.echo(f"Migrated {len(records)} records for user {user_id}.")


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
    token = environ.get(token_env)
    if token:
        return token
    msg = f"Environment variable '{token_env}' is required for polling GitHub notifications."
    raise click.ClickException(msg)


def _config_path_from_context(ctx: click.Context) -> Path:
    config_path = ctx.obj.get("config_path") if ctx.obj else None
    if isinstance(config_path, Path):
        return config_path
    msg = "Missing config path in CLI context."
    raise click.ClickException(msg)
