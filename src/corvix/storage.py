"""Local persistence for polled notifications."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import psycopg  # type: ignore[import]

from corvix.domain import Notification, NotificationRecord, format_timestamp, parse_timestamp


class StorageBackend(Protocol):
    """Protocol for notification persistence backends."""

    def save_records(
        self,
        user_id: str,
        records: list[NotificationRecord],
        generated_at: datetime,
    ) -> None: ...

    def load_records(self, user_id: str) -> tuple[datetime | None, list[NotificationRecord]]: ...

    def dismiss_record(self, user_id: str, thread_id: str) -> None: ...

    def get_dismissed_thread_ids(self, user_id: str) -> list[str]: ...


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
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

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
        user_id: str,
        records: list[NotificationRecord],
        generated_at: datetime,
    ) -> None:
        """Save records; user_id ignored in single-user mode."""
        self.save(records, generated_at)

    def load_records(self, user_id: str) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load records; user_id ignored in single-user mode."""
        return self.load()

    def dismiss_record(self, user_id: str, thread_id: str) -> None:
        """Mark a record as dismissed by thread_id in the JSON file."""
        generated_at, records = self.load()
        updated = False
        for record in records:
            if record.notification.thread_id == thread_id:
                record.dismissed = True
                updated = True
        if updated:
            self.save(records, generated_at)

    def get_dismissed_thread_ids(self, user_id: str) -> list[str]:
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

    def _connect(self) -> object:
        return psycopg.connect(self.connection_string)

    def save_records(
        self,
        user_id: str,
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
                             excluded, matched_rules, actions_taken, dismissed, snapshot_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                            record.dismissed,
                            generated_at,
                        ),
                    )
            conn.commit()

    def load_records(self, user_id: str) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load all records for user_id ordered by snapshot_at descending."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT thread_id, repository, reason, subject_title, subject_type,
                           unread, updated_at, thread_url, web_url, score, excluded,
                           matched_rules, actions_taken, dismissed, snapshot_at
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
            (
                thread_id,
                repository,
                reason,
                subject_title,
                subject_type,
                unread,
                updated_at,
                thread_url,
                web_url,
                score,
                excluded,
                matched_rules,
                actions_taken,
                dismissed,
                snapshot_at,
            ) = row
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
                    score=float(score),
                    excluded=bool(excluded),
                    matched_rules=list(matched_rules or []),
                    actions_taken=list(actions_taken or []),
                    dismissed=bool(dismissed),
                )
            )
        return latest_snapshot, records

    def dismiss_record(self, user_id: str, thread_id: str) -> None:
        """Set dismissed=true for a specific thread_id."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE notification_records SET dismissed = true WHERE user_id = %s AND thread_id = %s",
                    (user_id, thread_id),
                )
            conn.commit()

    def get_dismissed_thread_ids(self, user_id: str) -> list[str]:
        """Return thread_ids where dismissed=true for user_id."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT thread_id FROM notification_records WHERE user_id = %s AND dismissed = true",
                    (user_id,),
                )
                rows = cur.fetchall()
        return [row[0] for row in rows]
