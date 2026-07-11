"""A JSON-file ``StorageBackend`` double for tests.

Production persistence is PostgreSQL-only (``corvix.storage.PostgresStorage``).
The tests, however, need a lightweight file-backed backend they can inject via
``set_storage_backend`` or return from a monkeypatched ``_build_storage`` — one
that reads and writes the ``notifications.json`` snapshot format directly so a
test can seed a file and have the app read it back.

This is the retired legacy JSON cache, kept only as test infrastructure: it
implements the ``StorageBackend`` protocol over a single JSON file, minus the
production-grade ``fcntl`` locking and ``fsync`` durability that the old
production class carried (tests are single-process, so neither is needed).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from corvix.domain import (
    NotificationRecord,
    PollerStatus,
    format_timestamp,
    notification_key,
    parse_timestamp,
)
from corvix.storage import _parse_account_errors

_UNKNOWN_STATUS = PollerStatus(status="unknown", last_poll_time=None, last_error=None, last_error_time=None)


@dataclass(slots=True)
class JsonFileStorage:
    """Read/write notification snapshots to a JSON file (test-only backend)."""

    path: Path

    @staticmethod
    def _opt_str(value: object) -> str | None:
        return value if isinstance(value, str) else None

    def save(
        self,
        records: list[NotificationRecord],
        generated_at: datetime | None = None,
        *,
        poller_status: PollerStatus | None = None,
    ) -> None:
        """Persist records to disk, preserving prior dismissals and status."""
        timestamp = generated_at if generated_at is not None else datetime.now(tz=UTC)
        try:
            _, existing_records = self._load()
        except (ValueError, OSError):
            existing_records = []
        if poller_status is None:
            try:
                existing_status: PollerStatus | None = self._load_status()
            except (ValueError, OSError):
                existing_status = None
        else:
            existing_status = None
        dismissed_ids = {notification_key(record.notification) for record in existing_records if record.dismissed}
        status_to_save = poller_status if poller_status is not None else existing_status
        records_to_save = [
            replace(record, dismissed=record.dismissed or notification_key(record.notification) in dismissed_ids)
            for record in records
        ]
        self._write(records=records_to_save, generated_at=timestamp, poller_status=status_to_save)

    def load(self) -> tuple[datetime | None, list[NotificationRecord]]:
        """Load snapshot from disk if available."""
        if not self._exists():
            return None, []
        return self._load()

    def save_status(self, status: PollerStatus) -> None:
        """Persist only the poller status without touching notifications."""
        try:
            _, records = self._load()
            generated_raw = self._load_raw_generated_at()
        except (ValueError, OSError):
            records = []
            generated_at = datetime.now(tz=UTC)
        else:
            generated_at = _coerce_timestamp(generated_raw)
        self._write(records=records, generated_at=generated_at, poller_status=status)

    def load_status(self) -> PollerStatus:
        """Load the poller status from the cache file."""
        if not self._exists():
            return _UNKNOWN_STATUS
        return self._load_status()

    # --- StorageBackend protocol methods ---

    def save_records(self, records: list[NotificationRecord], generated_at: datetime) -> None:
        self.save(records, generated_at)

    def load_records(self) -> tuple[datetime | None, list[NotificationRecord]]:
        return self.load()

    def dismiss_record(self, thread_id: str, account_id: str = "primary") -> None:
        self._update_record(thread_id=thread_id, account_id=account_id, mutate=lambda r: replace(r, dismissed=True))

    def mark_record_read(self, thread_id: str, account_id: str = "primary") -> None:
        def _mark(record: NotificationRecord) -> NotificationRecord | None:
            if not record.notification.unread:
                return None
            return replace(record, notification=replace(record.notification, unread=False))

        self._update_record(thread_id=thread_id, account_id=account_id, mutate=_mark)

    def prune_orphaned_records(self, account_ids: Sequence[str]) -> int:
        ids = list(account_ids)
        if not ids:
            return 0
        generated_at, records = self._load() if self._exists() else (None, [])
        kept = [record for record in records if record.notification.account_id in ids]
        deleted = len(records) - len(kept)
        if deleted == 0:
            return 0
        timestamp = generated_at if generated_at is not None else datetime.now(tz=UTC)
        try:
            existing_status: PollerStatus | None = self._load_status()
        except (ValueError, OSError):
            existing_status = None
        self._write(records=kept, generated_at=timestamp, poller_status=existing_status)
        return deleted

    def get_dismissed_notification_keys(self) -> list[str]:
        _, records = self.load()
        return [notification_key(r.notification) for r in records if r.dismissed]

    def get_dismissed_thread_ids(self) -> list[str]:
        _, records = self.load()
        return [r.notification.thread_id for r in records if r.dismissed]

    def close(self) -> None:
        """No-op; the JSON backend holds no long-lived resources."""

    def __enter__(self) -> JsonFileStorage:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    # --- internal helpers ---

    def _exists(self) -> bool:
        try:
            return self.path.exists()
        except OSError:
            return False

    def _update_record(
        self,
        *,
        thread_id: str,
        account_id: str,
        mutate: Callable[[NotificationRecord], NotificationRecord | None],
    ) -> None:
        """Apply *mutate* to the matching record and rewrite the file if it changed."""
        generated_at, records = self._load() if self._exists() else (None, [])
        updated = False
        updated_records: list[NotificationRecord] = []
        for record in records:
            matches = record.notification.account_id == account_id and record.notification.thread_id == thread_id
            new_record = mutate(record) if matches else None
            if new_record is not None:
                updated_records.append(new_record)
                updated = True
            else:
                updated_records.append(record)
        if not updated:
            return
        timestamp = generated_at if generated_at is not None else datetime.now(tz=UTC)
        try:
            existing_status: PollerStatus | None = self._load_status()
        except (ValueError, OSError):
            existing_status = None
        self._write(records=updated_records, generated_at=timestamp, poller_status=existing_status)

    def _load_raw_generated_at(self) -> str | None:
        if not self.path.exists():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        raw = payload.get("generated_at") if isinstance(payload, dict) else None
        return raw if isinstance(raw, str) else None

    def _load_status(self) -> PollerStatus:
        """Read the poller status, propagating ``JSONDecodeError`` on a corrupt file.

        The health check relies on a corrupt cache surfacing as an error (so it
        can report ``invalid_cache``); the ``save*`` callers guard the call with
        ``except (ValueError, OSError)`` (``JSONDecodeError`` is a ``ValueError``).
        """
        if not self.path.exists():
            return _UNKNOWN_STATUS
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        raw = payload.get("poller_status") if isinstance(payload, dict) else None
        if isinstance(raw, dict):
            return PollerStatus(
                status=self._opt_str(raw.get("status")) or "unknown",
                last_poll_time=self._opt_str(raw.get("last_poll_time")),
                last_error=self._opt_str(raw.get("last_error")),
                last_error_time=self._opt_str(raw.get("last_error_time")),
                account_errors=_parse_account_errors(raw.get("account_errors")),
            )
        return _UNKNOWN_STATUS

    def _load(self) -> tuple[datetime | None, list[NotificationRecord]]:
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

    def _write(
        self,
        records: list[NotificationRecord],
        generated_at: datetime,
        *,
        poller_status: PollerStatus | None,
    ) -> None:
        payload: dict[str, object] = {
            "generated_at": format_timestamp(generated_at),
            "notifications": [record.to_dict() for record in records],
        }
        if poller_status is not None:
            payload["poller_status"] = asdict(poller_status)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _coerce_timestamp(raw: str | None) -> datetime:
    if raw:
        try:
            return parse_timestamp(raw)
        except ValueError:
            return datetime.now(tz=UTC)
    return datetime.now(tz=UTC)
