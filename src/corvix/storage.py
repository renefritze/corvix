"""Local persistence for polled notifications."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import psycopg
from psycopg.types.json import Jsonb

from corvix.domain import Notification, NotificationRecord, format_timestamp, parse_timestamp
from corvix.types import UserId

_NOTIFICATION_RECORD_COLUMNS = 16


class StorageBackend(Protocol):
    """Protocol for notification persistence backends."""

    def save_records(
        self,
        user_id: UserId,
        records: list[NotificationRecord],
        generated_at: datetime,
    ) -> None: ...

    def load_records(self, user_id: UserId) -> tuple[datetime | None, list[NotificationRecord]]: ...

    def dismiss_record(self, user_id: UserId, thread_id: str) -> None: ...

    def mark_record_read(self, user_id: UserId, thread_id: str) -> None: ...

    def get_dismissed_thread_ids(self, user_id: UserId) -> list[str]: ...


@dataclass(slots=True)
class NotificationCache:
    """Read/write notification snapshots to a JSON file.

    Implements StorageBackend using a single-user JSON file.
    The user_id parameter in protocol methods is ignored — the file is shared.
    """

    path: Path

    def save(self, records: list[NotificationRecord], generated_at: datetime | None = None) -> None:
        """Persist records to disk."""
        timestamp = generated_at if generated_at is not None else datetime.now(tz=UTC)
        payload = {
            "generated_at": format_timestamp(timestamp),
            "notifications": [record.to_dict() for record in records],
        }
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

    def load(self) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load snapshot from disk if available."""
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

    def dismiss_record(self, user_id: UserId, thread_id: str) -> None:
        """Mark a record as dismissed by thread_id in the JSON file."""
        generated_at, records = self.load()
        updated = False
        for record in records:
            if record.notification.thread_id == thread_id:
                record.dismissed = True
                updated = True
        if updated:
            self.save(records, generated_at)

    def mark_record_read(self, user_id: UserId, thread_id: str) -> None:
        """Mark a record as read by thread_id in the JSON file."""
        generated_at, records = self.load()
        updated = False
        for record in records:
            if record.notification.thread_id == thread_id and record.notification.unread:
                record.notification.unread = False
                updated = True
        if updated:
            self.save(records, generated_at)

    def get_dismissed_thread_ids(self, user_id: UserId) -> list[str]:
        """Return thread_ids of dismissed records."""
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
                            (user_id, thread_id, repository, reason, subject_title,
                             subject_type, unread, updated_at, thread_url, web_url, score,
                             excluded, matched_rules, actions_taken, context, dismissed, snapshot_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, thread_id) DO UPDATE SET
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
            unread = _require_bool(row[5], "unread")
            updated_at = _require_datetime(row[6], "updated_at")
            thread_url = _optional_str(row[7], "thread_url")
            web_url = _optional_str(row[8], "web_url")
            score = _require_float(row[9], "score")
            excluded = _require_bool(row[10], "excluded")
            matched_rules = _coerce_str_list(row[11], "matched_rules")
            actions_taken = _coerce_str_list(row[12], "actions_taken")
            context = row[13]
            dismissed = _require_bool(row[14], "dismissed")
            snapshot_at = _require_datetime(row[15], "snapshot_at")
            if latest_snapshot is None:
                latest_snapshot = snapshot_at
            notification = Notification(
                thread_id=thread_id,
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

    def dismiss_record(self, user_id: UserId, thread_id: str) -> None:
        """Set dismissed=true for a specific thread_id."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE notification_records SET dismissed = true WHERE user_id = %s AND thread_id = %s",
                    (user_id, thread_id),
                )
            conn.commit()

    def mark_record_read(self, user_id: UserId, thread_id: str) -> None:
        """Set unread=false for a specific thread_id."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE notification_records SET unread = false WHERE user_id = %s AND thread_id = %s",
                    (user_id, thread_id),
                )
            conn.commit()

    def get_dismissed_thread_ids(self, user_id: UserId) -> list[str]:
        """Return thread_ids where dismissed=true for user_id."""
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
    if isinstance(value, dict):
        output: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            output[key] = item
        return output
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            output: dict[str, object] = {}
            for key, item in parsed.items():
                if not isinstance(key, str):
                    continue
                output[key] = item
            return output
    return {}


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
