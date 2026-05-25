"""Local persistence for polled notifications.

The JSON cache uses ``fcntl`` advisory locks and is therefore supported on
Linux/POSIX platforms only.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

import psycopg
import psycopg_pool
from psycopg.types.json import Jsonb

from corvix.db import get_database_url
from corvix.domain import (
    Notification,
    NotificationRecord,
    PollerStatus,
    format_timestamp,
    notification_key,
    parse_timestamp,
)
from corvix.types import UserId

if TYPE_CHECKING:
    from corvix.config import AppConfig

_NOTIFICATION_RECORD_COLUMNS = 18
_DISMISSED_ROW_COLUMNS = 2
_POLLER_STATUS_COLUMNS = 4

# Fixed identity used for the single-user deployment. Multi-user deployments
# scope records per real user; single-user mode shares this seeded row (created
# by the Alembic migration that introduced the ``poller_status`` table).
SINGLE_USER_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")


class StorageConfigError(RuntimeError):
    """Raised when required storage configuration (a database URL) is missing."""


class StorageBackend(Protocol):
    """Protocol for notification persistence backends."""

    def save_records(
        self,
        user_id: UserId,
        records: list[NotificationRecord],
        generated_at: datetime,
    ) -> None: ...

    def load_records(self, user_id: UserId) -> tuple[datetime | None, list[NotificationRecord]]: ...

    def save_status(self, user_id: UserId, status: PollerStatus) -> None: ...

    def load_status(self, user_id: UserId) -> PollerStatus: ...

    def dismiss_record(self, user_id: UserId, thread_id: str, account_id: str = "primary") -> None: ...

    def mark_record_read(self, user_id: UserId, thread_id: str, account_id: str = "primary") -> None: ...

    def get_dismissed_notification_keys(self, user_id: UserId) -> list[str]: ...

    def get_dismissed_thread_ids(self, user_id: UserId) -> list[str]: ...

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
class NotificationCache:
    """Read/write notification snapshots to a JSON file.

    Implements StorageBackend using a single-user JSON file.
    The user_id parameter in protocol methods is ignored — the file is shared.
    """

    path: Path

    @staticmethod
    def _opt_str(value: object) -> str | None:
        if isinstance(value, str):
            return value
        return None

    def save(
        self,
        records: list[NotificationRecord],
        generated_at: datetime | None = None,
        *,
        poller_status: PollerStatus | None = None,
    ) -> None:
        """Persist records to disk."""
        timestamp = generated_at if generated_at is not None else datetime.now(tz=UTC)
        with self._exclusive_lock():
            try:
                _, existing_records = self._load_unlocked()
            except (ValueError, OSError):
                existing_records = []
            if poller_status is None:
                try:
                    existing_status = self._load_status_unlocked()
                except (ValueError, OSError):
                    existing_status = None
            else:
                existing_status = None
            dismissed_ids = {notification_key(record.notification) for record in existing_records if record.dismissed}
            status_to_save = poller_status if poller_status is not None else existing_status
            records_to_save = [
                NotificationRecord(
                    notification=record.notification,
                    score=record.score,
                    excluded=record.excluded,
                    matched_rules=record.matched_rules,
                    actions_taken=record.actions_taken,
                    dismissed=record.dismissed or notification_key(record.notification) in dismissed_ids,
                    context=record.context,
                )
                for record in records
            ]
            self._save_unlocked(records=records_to_save, generated_at=timestamp, poller_status=status_to_save)

    def load(self) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load snapshot from disk if available."""
        try:
            path_exists = self.path.exists()
        except OSError:
            return None, []
        if not path_exists:
            return None, []
        with self._shared_lock():
            return self._load_unlocked()

    def save_status(self, user_id: UserId, status: PollerStatus) -> None:
        """Persist only the poller status without touching notifications.

        ``user_id`` is ignored in single-user JSON mode.
        """
        _ = user_id
        with self._exclusive_lock():
            try:
                _, records = self._load_unlocked()
                generated_raw = self._load_raw_generated_at()
            except (ValueError, OSError):
                records: list[NotificationRecord] = []
                generated_at = datetime.now(tz=UTC)
            else:
                if generated_raw:
                    try:
                        generated_at = parse_timestamp(generated_raw)
                    except ValueError:
                        generated_at = datetime.now(tz=UTC)
                else:
                    generated_at = datetime.now(tz=UTC)
            self._save_unlocked(records=records, generated_at=generated_at, poller_status=status)

    def load_status(self, user_id: UserId = "") -> PollerStatus:
        """Load the poller status from the cache file.

        ``user_id`` is ignored in single-user JSON mode.
        """
        _ = user_id
        try:
            path_exists = self.path.exists()
        except OSError:
            return PollerStatus(status="unknown", last_poll_time=None, last_error=None, last_error_time=None)
        if not path_exists:
            return PollerStatus(status="unknown", last_poll_time=None, last_error=None, last_error_time=None)
        with self._shared_lock():
            return self._load_status_unlocked()

    def _load_raw_generated_at(self) -> str | None:
        if not self.path.exists():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if isinstance(payload, dict):
            raw = payload.get("generated_at")
            if isinstance(raw, str):
                return raw
        return None

    def _load_status_unlocked(self) -> PollerStatus:
        if not self.path.exists():
            return PollerStatus(status="unknown", last_poll_time=None, last_error=None, last_error_time=None)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            raw = payload.get("poller_status")
            if isinstance(raw, dict):
                return PollerStatus(
                    status=self._opt_str(raw.get("status")) or "unknown",
                    last_poll_time=self._opt_str(raw.get("last_poll_time")),
                    last_error=self._opt_str(raw.get("last_error")),
                    last_error_time=self._opt_str(raw.get("last_error_time")),
                )
        return PollerStatus(status="unknown", last_poll_time=None, last_error=None, last_error_time=None)

    def _load_unlocked(self) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load snapshot from disk without acquiring a file lock."""
        if not self.path.exists():
            return None, []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raise ValueError("Invalid cache file format: cannot parse JSON.") from None
        if not isinstance(payload, dict):
            msg = "Invalid cache file format."
            raise ValueError(msg)
        generated_raw = payload.get("generated_at")
        generated_at = parse_timestamp(generated_raw) if isinstance(generated_raw, str) else None
        raw_notifications = payload.get("notifications", [])
        if not isinstance(raw_notifications, list):
            msg = "Invalid cache file format: 'notifications' must be a list."
            raise ValueError(msg)
        records = [NotificationRecord.from_dict(item) for item in raw_notifications if isinstance(item, dict)]
        return generated_at, records

    def _save_unlocked(
        self, records: list[NotificationRecord], generated_at: datetime, *, poller_status: PollerStatus | None = None
    ) -> None:
        status_to_save = poller_status
        if status_to_save is None:
            try:
                status_to_save = self._load_status_unlocked()
            except (ValueError, OSError):
                status_to_save = None
        payload: dict[str, object] = {
            "generated_at": format_timestamp(generated_at),
            "notifications": [record.to_dict() for record in records],
        }
        if status_to_save is not None:
            payload["poller_status"] = asdict(status_to_save)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(payload, indent=2)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_file.write(content)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = Path(temp_file.name)
            temp_path.replace(self.path)
            _fsync_directory(self.path.parent)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.parent / f".{self.path.name}.lock"
        with lock_path.open("a", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @contextmanager
    def _shared_lock(self) -> Iterator[None]:
        """Acquire a shared read lock when possible; fall through unlocked otherwise.

        When the lock file cannot be created (read-only filesystem, missing
        permissions), no concurrent writer can be holding the exclusive lock
        from this process either, so reads proceed without it. Torn reads
        remain prevented under normal operation where both reader and writer
        can open the lock file.
        """
        lock_path = self.path.parent / f".{self.path.name}.lock"
        try:
            lock_file = lock_path.open("a+", encoding="utf-8")
        except OSError:
            yield
            return

        with lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_SH)
            except OSError:
                yield
                return
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    # --- StorageBackend protocol methods ---

    def save_records(
        self,
        user_id: UserId,
        records: list[NotificationRecord],
        generated_at: datetime,
    ) -> None:
        """Save records; user_id ignored in single-user mode."""
        self.save(records, generated_at)

    def load_records(self, user_id: UserId) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load records; user_id ignored in single-user mode."""
        return self.load()

    def dismiss_record(self, user_id: UserId, thread_id: str, account_id: str = "primary") -> None:
        """Mark a record as dismissed by account/thread id in the JSON file."""
        _ = user_id
        with self._exclusive_lock():
            generated_at, records = self._load_unlocked()
            updated = False
            updated_records = []
            for record in records:
                if record.notification.account_id == account_id and record.notification.thread_id == thread_id:
                    updated_records.append(replace(record, dismissed=True))
                    updated = True
                else:
                    updated_records.append(record)
            records = updated_records
            if updated:
                timestamp = generated_at if generated_at is not None else datetime.now(tz=UTC)
                try:
                    existing_status = self._load_status_unlocked()
                except (ValueError, OSError):
                    existing_status = None
                self._save_unlocked(records=records, generated_at=timestamp, poller_status=existing_status)

    def mark_record_read(self, user_id: UserId, thread_id: str, account_id: str = "primary") -> None:
        """Mark a record as read by account/thread id in the JSON file."""
        _ = user_id
        with self._exclusive_lock():
            generated_at, records = self._load_unlocked()
            updated = False
            updated_records = []
            for record in records:
                if (
                    record.notification.account_id == account_id
                    and record.notification.thread_id == thread_id
                    and record.notification.unread
                ):
                    new_notification = replace(record.notification, unread=False)
                    updated_records.append(replace(record, notification=new_notification))
                    updated = True
                else:
                    updated_records.append(record)
            records = updated_records
            if updated:
                timestamp = generated_at if generated_at is not None else datetime.now(tz=UTC)
                try:
                    existing_status = self._load_status_unlocked()
                except (ValueError, OSError):
                    existing_status = None
                self._save_unlocked(records=records, generated_at=timestamp, poller_status=existing_status)

    def get_dismissed_notification_keys(self, user_id: UserId) -> list[str]:
        """Return account-scoped keys of dismissed records."""
        _ = user_id
        _, records = self.load()
        return [notification_key(r.notification) for r in records if r.dismissed]

    def get_dismissed_thread_ids(self, user_id: UserId) -> list[str]:
        """Backward-compatible API returning only thread IDs."""
        _ = user_id
        _, records = self.load()
        return [r.notification.thread_id for r in records if r.dismissed]

    def close(self) -> None:
        """No-op; the JSON backend holds no long-lived resources."""

    def __enter__(self) -> NotificationCache:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


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
        user_id: UserId,
        records: list[NotificationRecord],
        generated_at: datetime,
    ) -> None:
        """Upsert records for user_id. Preserves dismissed flag on conflict."""
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
                            user_id,
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

    def load_records(self, user_id: UserId) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load all records for user_id ordered by snapshot_at descending."""
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
                    (user_id,),
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

    def save_status(self, user_id: UserId, status: PollerStatus) -> None:
        """Upsert the poller status row for ``user_id``."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO poller_status
                        (user_id, status, last_poll_time, last_error, last_error_time, updated_at)
                    VALUES (%s, %s, %s, %s, %s, now())
                    ON CONFLICT (user_id) DO UPDATE SET
                        status          = EXCLUDED.status,
                        last_poll_time  = EXCLUDED.last_poll_time,
                        last_error      = EXCLUDED.last_error,
                        last_error_time = EXCLUDED.last_error_time,
                        updated_at      = now()
                    """,
                    (
                        user_id,
                        status.status,
                        status.last_poll_time,
                        status.last_error,
                        status.last_error_time,
                    ),
                )
            conn.commit()

    def load_status(self, user_id: UserId) -> PollerStatus:
        """Load the poller status for ``user_id``, defaulting to ``unknown``."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, last_poll_time, last_error, last_error_time FROM poller_status WHERE user_id = %s",
                    (user_id,),
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
        )

    def dismiss_record(self, user_id: UserId, thread_id: str, account_id: str = "primary") -> None:
        """Set dismissed=true for a specific account/thread id."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE notification_records SET dismissed = true WHERE user_id = %s AND account_id = %s AND thread_id = %s",
                    (user_id, account_id, thread_id),
                )
            conn.commit()

    def mark_record_read(self, user_id: UserId, thread_id: str, account_id: str = "primary") -> None:
        """Set unread=false for a specific account/thread id."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE notification_records SET unread = false WHERE user_id = %s AND account_id = %s AND thread_id = %s",
                    (user_id, account_id, thread_id),
                )
            conn.commit()

    def get_dismissed_notification_keys(self, user_id: UserId) -> list[str]:
        """Return account-scoped keys where dismissed=true for user_id."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT account_id, thread_id FROM notification_records WHERE user_id = %s AND dismissed = true",
                    (user_id,),
                )
                rows = cur.fetchall()
        dismissed_ids: list[str] = []
        for row in rows:
            if not row or len(row) < _DISMISSED_ROW_COLUMNS:
                continue
            dismissed_ids.append(f"{_require_str(row[0], 'account_id')}:{_require_str(row[1], 'thread_id')}")
        return dismissed_ids

    def get_dismissed_thread_ids(self, user_id: UserId) -> list[str]:
        """Backward-compatible API returning only thread IDs."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT thread_id FROM notification_records WHERE user_id = %s AND dismissed = true",
                    (user_id,),
                )
                rows = cur.fetchall()
        dismissed_ids: list[str] = []
        for row in rows:
            if not row:
                continue
            dismissed_ids.append(_require_str(row[0], "thread_id"))
        return dismissed_ids


def _fsync_directory(path: Path) -> None:
    """Best-effort fsync of a directory after atomic replacement."""
    try:
        dir_fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        return
    finally:
        os.close(dir_fd)


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
