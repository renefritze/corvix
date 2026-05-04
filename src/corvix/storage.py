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
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import psycopg
from psycopg.types.json import Jsonb

from corvix.domain import (
    Notification,
    NotificationRecord,
    PollerStatus,
    format_timestamp,
    notification_key,
    parse_timestamp,
)
from corvix.types import UserId

_NOTIFICATION_RECORD_COLUMNS = 18
_DISMISSED_ROW_COLUMNS = 2


class StorageBackend(Protocol):
    """Protocol for notification persistence backends."""

    def save_records(
        self,
        user_id: UserId,
        records: list[NotificationRecord],
        generated_at: datetime,
    ) -> None: ...

    def load_records(self, user_id: UserId) -> tuple[datetime | None, list[NotificationRecord]]: ...

    def dismiss_record(self, user_id: UserId, thread_id: str, account_id: str = "primary") -> None: ...

    def mark_record_read(self, user_id: UserId, thread_id: str, account_id: str = "primary") -> None: ...

    def get_dismissed_notification_keys(self, user_id: UserId) -> list[str]: ...

    def get_dismissed_thread_ids(self, user_id: UserId) -> list[str]: ...


@dataclass(slots=True)
class NotificationCache:
    """Read/write notification snapshots to a JSON file.

    Implements StorageBackend using a single-user JSON file.
    The user_id parameter in protocol methods is ignored — the file is shared.
    """

    path: Path

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
            except ValueError:
                existing_records = []
            if poller_status is None:
                try:
                    existing_status = self._load_status_unlocked()
                except (json.JSONDecodeError, ValueError, OSError):
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
                    matched_rules=list(record.matched_rules),
                    actions_taken=list(record.actions_taken),
                    dismissed=record.dismissed or notification_key(record.notification) in dismissed_ids,
                    context=record.context,
                )
                for record in records
            ]
            self._save_unlocked(records=records_to_save, generated_at=timestamp, poller_status=status_to_save)

    def load(self) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load snapshot from disk if available."""
        return self._load_unlocked()

    def save_status(self, status: PollerStatus) -> None:
        """Persist only the poller status without touching notifications."""
        with self._exclusive_lock():
            try:
                _, records = self._load_unlocked()
                generated_raw = self._load_raw_generated_at()
                generated_at = parse_timestamp(generated_raw) if generated_raw else datetime.now(tz=UTC)
            except (json.JSONDecodeError, ValueError, OSError):
                records: list[NotificationRecord] = []
                generated_at = datetime.now(tz=UTC)
            self._save_unlocked(records=records, generated_at=generated_at, poller_status=status)

    def load_status(self) -> PollerStatus:
        """Load the poller status from the cache file."""
        return self._load_status_unlocked()

    def _load_raw_generated_at(self) -> str | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
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
                status_value = raw.get("status")
                return PollerStatus(
                    status=status_value if isinstance(status_value, str) else "unknown",
                    last_poll_time=raw.get("last_poll_time") if isinstance(raw.get("last_poll_time"), str) else None,
                    last_error=raw.get("last_error") if isinstance(raw.get("last_error"), str) else None,
                    last_error_time=raw.get("last_error_time") if isinstance(raw.get("last_error_time"), str) else None,
                )
        return PollerStatus(status="unknown", last_poll_time=None, last_error=None, last_error_time=None)

    def _load_unlocked(self) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load snapshot from disk without acquiring a file lock."""
        if not self.path.exists():
            return None, []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
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
        payload: dict[str, object] = {
            "generated_at": format_timestamp(generated_at),
            "notifications": [record.to_dict() for record in records],
        }
        if poller_status is not None:
            payload["poller_status"] = dict(poller_status)
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
            for record in records:
                if record.notification.account_id == account_id and record.notification.thread_id == thread_id:
                    record.dismissed = True
                    updated = True
            if updated:
                timestamp = generated_at if generated_at is not None else datetime.now(tz=UTC)
                try:
                    existing_status = self._load_status_unlocked()
                except (json.JSONDecodeError, ValueError, OSError):
                    existing_status = None
                self._save_unlocked(records=records, generated_at=timestamp, poller_status=existing_status)

    def mark_record_read(self, user_id: UserId, thread_id: str, account_id: str = "primary") -> None:
        """Mark a record as read by account/thread id in the JSON file."""
        _ = user_id
        with self._exclusive_lock():
            generated_at, records = self._load_unlocked()
            updated = False
            for record in records:
                if (
                    record.notification.account_id == account_id
                    and record.notification.thread_id == thread_id
                    and record.notification.unread
                ):
                    record.notification.unread = False
                    updated = True
            if updated:
                timestamp = generated_at if generated_at is not None else datetime.now(tz=UTC)
                try:
                    existing_status = self._load_status_unlocked()
                except (json.JSONDecodeError, ValueError, OSError):
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


@dataclass(slots=True)
class PostgresStorage:
    """PostgreSQL-backed notification persistence implementing StorageBackend.

    Uses psycopg (sync) so it is safe to use from CLI commands and the
    synchronous Litestar route handlers (sync_to_thread=False is not used
    with this backend — callers should run in a thread pool if needed).
    """

    connection_string: str

    def _connect(self) -> psycopg.Connection[tuple[object, ...]]:
        return psycopg.connect(self.connection_string)

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
                            record.matched_rules,
                            record.actions_taken,
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
                    matched_rules=matched_rules,
                    actions_taken=actions_taken,
                    context=_coerce_context(context),
                    dismissed=dismissed,
                )
            )
        return latest_snapshot, records

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
