"""Local persistence for polled notifications.

PostgreSQL is the only supported backend; :class:`PostgresStorage` implements
the :class:`StorageBackend` protocol used across the app.
"""

from __future__ import annotations

import json
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

import psycopg
import psycopg_pool
from psycopg.types.json import Jsonb

from corvix.db import get_database_url
from corvix.domain import (
    AccountError,
    Notification,
    NotificationRecord,
    PollerStatus,
)

if TYPE_CHECKING:
    from corvix.config import AppConfig

_NOTIFICATION_RECORD_COLUMNS = 18
_DISMISSED_ROW_COLUMNS = 2
_POLLER_STATUS_COLUMNS = 5

# Fixed UUID for the single-user deployment. All records are scoped to this identity
# (created by the Alembic migration that introduced the ``poller_status`` table).
SINGLE_USER_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")


class StorageConfigError(RuntimeError):
    """Raised when required storage configuration (a database URL) is missing."""


class StorageBackend(Protocol):
    """Protocol for notification persistence backends."""

    def save_records(
        self,
        records: list[NotificationRecord],
        generated_at: datetime,
    ) -> None: ...

    def load_records(self) -> tuple[datetime | None, list[NotificationRecord]]: ...

    def save_status(self, status: PollerStatus) -> None: ...

    def load_status(self) -> PollerStatus: ...

    def dismiss_record(self, thread_id: str, account_id: str = "primary") -> None: ...

    def mark_record_read(self, thread_id: str, account_id: str = "primary") -> None: ...

    def get_dismissed_notification_keys(self) -> list[str]: ...

    def get_dismissed_thread_ids(self) -> list[str]: ...

    def close(self) -> None: ...

    def __enter__(self) -> StorageBackend: ...

    def __exit__(self, *args: object) -> None: ...


def create_storage(config: AppConfig) -> PostgresStorage:
    """Return the configured PostgreSQL storage backend.

    PostgreSQL is required in all deployments; the JSON cache is no longer used
    as the shared store between the poller and the web service. Raises
    :class:`StorageConfigError` when no database URL is configured.
    """
    db_url = get_database_url(config.database.url_env)
    if not db_url:
        msg = (
            f"PostgreSQL is required but no database URL is configured. "
            f"Set '{config.database.url_env}' (or '{config.database.url_env}_FILE')."
        )
        raise StorageConfigError(msg)
    return PostgresStorage(connection_string=db_url)


@dataclass(slots=True)
class PostgresStorage:
    """PostgreSQL-backed notification persistence implementing StorageBackend.

    Uses psycopg (sync) so it is safe to use from CLI commands and the
    synchronous Litestar route handlers (sync_to_thread=False is not used
    with this backend — callers should run in a thread pool if needed).

    A ``psycopg_pool.ConnectionPool`` is created at construction time so that
    TCP connections are reused across method calls rather than being opened and
    torn down per operation.  Call :meth:`close` when the storage is no longer
    needed, or use it as a context manager::

        with PostgresStorage(connection_string=url) as storage:
            storage.save_records(...)
    """

    connection_string: str
    min_pool_size: int = 1
    max_pool_size: int = 10
    _pool: psycopg_pool.ConnectionPool[psycopg.Connection[tuple[object, ...]]] | None = field(
        init=False, repr=False, compare=False, default=None
    )

    def __post_init__(self) -> None:
        self._pool = psycopg_pool.ConnectionPool(
            conninfo=self.connection_string,
            min_size=self.min_pool_size,
            max_size=self.max_pool_size,
        )

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close all pooled connections and release resources."""
        pool = self._pool
        if pool is not None:
            self._pool = None
            pool.close()

    def __enter__(self) -> PostgresStorage:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> AbstractContextManager[psycopg.Connection[tuple[object, ...]]]:
        """Return a pooled connection context-manager.

        Usage is identical to the previous ``psycopg.connect()`` call::

            with self._connect() as conn:
                ...
        """
        pool = self._pool
        if pool is None:
            msg = "PostgresStorage pool has been closed."
            raise RuntimeError(msg)
        return pool.connection()

    def save_records(
        self,
        records: list[NotificationRecord],
        generated_at: datetime,
    ) -> None:
        """Upsert records. Preserves dismissed flag on conflict."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                for record in records:
                    n = record.notification
                    cur.execute(
                        """
                        INSERT INTO notification_records
                            (user_id, account_id, account_label, thread_id, repository, reason, subject_title,
                              subject_type, unread, updated_at, thread_url, web_url, score,
                              excluded, matched_rules, actions_taken, context, dismissed, snapshot_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, account_id, thread_id) DO UPDATE SET
                            account_label = EXCLUDED.account_label,
                            repository    = EXCLUDED.repository,
                            reason        = EXCLUDED.reason,
                            subject_title = EXCLUDED.subject_title,
                            subject_type  = EXCLUDED.subject_type,
                            unread        = EXCLUDED.unread,
                            updated_at    = EXCLUDED.updated_at,
                            thread_url    = EXCLUDED.thread_url,
                            web_url       = EXCLUDED.web_url,
                            score         = EXCLUDED.score,
                            excluded      = EXCLUDED.excluded,
                            matched_rules = EXCLUDED.matched_rules,
                            actions_taken = EXCLUDED.actions_taken,
                            context       = EXCLUDED.context,
                            snapshot_at   = EXCLUDED.snapshot_at
                        """,
                        (
                            SINGLE_USER_ID,
                            n.account_id,
                            n.account_label,
                            n.thread_id,
                            n.repository,
                            n.reason,
                            n.subject_title,
                            n.subject_type,
                            n.unread,
                            n.updated_at,
                            n.thread_url,
                            n.web_url,
                            record.score,
                            record.excluded,
                            list(record.matched_rules),
                            list(record.actions_taken),
                            Jsonb(record.context),
                            record.dismissed,
                            generated_at,
                        ),
                    )
            conn.commit()

    def load_records(self) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load all records ordered by snapshot_at descending."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT thread_id, repository, reason, subject_title, subject_type,
                           account_id, account_label,
                           unread, updated_at, thread_url, web_url, score, excluded,
                           matched_rules, actions_taken, context, dismissed, snapshot_at
                    FROM notification_records
                    WHERE user_id = %s
                    ORDER BY snapshot_at DESC, score DESC
                    """,
                    (SINGLE_USER_ID,),
                )
                rows = cur.fetchall()

        if not rows:
            return None, []

        records: list[NotificationRecord] = []
        latest_snapshot: datetime | None = None
        for row in rows:
            if len(row) != _NOTIFICATION_RECORD_COLUMNS:
                msg = "Invalid row shape returned by notification_records query."
                raise ValueError(msg)
            thread_id = _require_str(row[0], "thread_id")
            repository = _require_str(row[1], "repository")
            reason = _require_str(row[2], "reason")
            subject_title = _require_str(row[3], "subject_title")
            subject_type = _require_str(row[4], "subject_type")
            account_id = _require_str(row[5], "account_id")
            account_label = _require_str(row[6], "account_label")
            unread = _require_bool(row[7], "unread")
            updated_at = _require_datetime(row[8], "updated_at")
            thread_url = _optional_str(row[9], "thread_url")
            web_url = _optional_str(row[10], "web_url")
            score = _require_float(row[11], "score")
            excluded = _require_bool(row[12], "excluded")
            matched_rules = _coerce_str_list(row[13], "matched_rules")
            actions_taken = _coerce_str_list(row[14], "actions_taken")
            context = row[15]
            dismissed = _require_bool(row[16], "dismissed")
            snapshot_at = _require_datetime(row[17], "snapshot_at")
            if latest_snapshot is None:
                latest_snapshot = snapshot_at
            notification = Notification(
                thread_id=thread_id,
                account_id=account_id,
                account_label=account_label,
                repository=repository,
                reason=reason,
                subject_title=subject_title,
                subject_type=subject_type,
                unread=unread,
                updated_at=updated_at,
                thread_url=thread_url,
                web_url=web_url,
            )
            records.append(
                NotificationRecord(
                    notification=notification,
                    score=score,
                    excluded=excluded,
                    matched_rules=tuple(matched_rules),
                    actions_taken=tuple(actions_taken),
                    context=_coerce_context(context),
                    dismissed=dismissed,
                )
            )
        return latest_snapshot, records

    def save_status(self, status: PollerStatus) -> None:
        """Upsert the poller status row."""
        account_errors_json = (
            Jsonb(
                [
                    {"account_id": e.account_id, "account_label": e.account_label, "error": e.error}
                    for e in status.account_errors
                ]
            )
            if status.account_errors
            else None
        )
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO poller_status
                        (user_id, status, last_poll_time, last_error, last_error_time, account_errors, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (user_id) DO UPDATE SET
                        status          = EXCLUDED.status,
                        last_poll_time  = EXCLUDED.last_poll_time,
                        last_error      = EXCLUDED.last_error,
                        last_error_time = EXCLUDED.last_error_time,
                        account_errors  = EXCLUDED.account_errors,
                        updated_at      = now()
                    """,
                    (
                        SINGLE_USER_ID,
                        status.status,
                        status.last_poll_time,
                        status.last_error,
                        status.last_error_time,
                        account_errors_json,
                    ),
                )
            conn.commit()

    def load_status(self) -> PollerStatus:
        """Load the poller status, defaulting to ``unknown``."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, last_poll_time, last_error, last_error_time, account_errors FROM poller_status WHERE user_id = %s",
                    (SINGLE_USER_ID,),
                )
                row = cur.fetchone()
        if row is None:
            return PollerStatus(status="unknown", last_poll_time=None, last_error=None, last_error_time=None)
        if len(row) != _POLLER_STATUS_COLUMNS:
            msg = "Invalid row shape returned by poller_status query."
            raise ValueError(msg)
        return PollerStatus(
            status=_require_str(row[0], "status"),
            last_poll_time=_optional_str(row[1], "last_poll_time"),
            last_error=_optional_str(row[2], "last_error"),
            last_error_time=_optional_str(row[3], "last_error_time"),
            account_errors=_parse_account_errors(row[4]),
        )

    def dismiss_record(self, thread_id: str, account_id: str = "primary") -> None:
        """Set dismissed=true for a specific account/thread id."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE notification_records SET dismissed = true WHERE user_id = %s AND account_id = %s AND thread_id = %s",
                    (SINGLE_USER_ID, account_id, thread_id),
                )
            conn.commit()

    def mark_record_read(self, thread_id: str, account_id: str = "primary") -> None:
        """Set unread=false for a specific account/thread id."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE notification_records SET unread = false WHERE user_id = %s AND account_id = %s AND thread_id = %s",
                    (SINGLE_USER_ID, account_id, thread_id),
                )
            conn.commit()

    def get_dismissed_notification_keys(self) -> list[str]:
        """Return account-scoped keys where dismissed=true."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT account_id, thread_id FROM notification_records WHERE user_id = %s AND dismissed = true",
                    (SINGLE_USER_ID,),
                )
                rows = cur.fetchall()
        dismissed_ids: list[str] = []
        for row in rows:
            if not row or len(row) < _DISMISSED_ROW_COLUMNS:
                continue
            dismissed_ids.append(f"{_require_str(row[0], 'account_id')}:{_require_str(row[1], 'thread_id')}")
        return dismissed_ids

    def get_dismissed_thread_ids(self) -> list[str]:
        """Return thread IDs of dismissed records."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT thread_id FROM notification_records WHERE user_id = %s AND dismissed = true",
                    (SINGLE_USER_ID,),
                )
                rows = cur.fetchall()
        dismissed_ids: list[str] = []
        for row in rows:
            if not row:
                continue
            dismissed_ids.append(_require_str(row[0], "thread_id"))
        return dismissed_ids


def _coerce_context(value: object) -> dict[str, object]:
    direct = _coerce_string_key_dict(value)
    if direct is not None:
        return direct
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        parsed_dict = _coerce_string_key_dict(parsed)
        if parsed_dict is not None:
            return parsed_dict
    return {}


def _coerce_string_key_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    output: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            continue
        output[key] = item
    return output


def _require_str(value: object, field: str) -> str:
    if isinstance(value, str):
        return value
    msg = f"Invalid value for '{field}': expected string."
    raise ValueError(msg)


def _optional_str(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, field)


def _require_bool(value: object, field: str) -> bool:
    if isinstance(value, bool):
        return value
    msg = f"Invalid value for '{field}': expected boolean."
    raise ValueError(msg)


def _require_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"Invalid value for '{field}': expected number."
        raise ValueError(msg)
    return float(value)


def _require_datetime(value: object, field: str) -> datetime:
    if isinstance(value, datetime):
        return value
    msg = f"Invalid value for '{field}': expected datetime."
    raise ValueError(msg)


def _parse_account_errors(value: object) -> tuple[AccountError, ...]:
    """Parse the account_errors JSONB value into a tuple of AccountError."""
    if not isinstance(value, list):
        return ()
    result: list[AccountError] = []
    for raw_item in value:
        if not isinstance(raw_item, dict):
            continue
        item: dict[str, object] = {str(k): v for k, v in raw_item.items()}
        account_id = item.get("account_id")
        account_label = item.get("account_label")
        error = item.get("error")
        if isinstance(account_id, str) and isinstance(account_label, str) and isinstance(error, str):
            result.append(AccountError(account_id=account_id, account_label=account_label, error=error))
    return tuple(result)


def _coerce_str_list(value: object, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        msg = f"Invalid value for '{field}': expected list of strings."
        raise ValueError(msg)
    output: list[str] = []
    for item in value:
        output.append(_require_str(item, field))
    return output
