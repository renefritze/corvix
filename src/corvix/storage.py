"""Local persistence for polled notifications."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from corvix.domain import NotificationRecord, format_timestamp, parse_timestamp


@dataclass(slots=True)
class NotificationCache:
    """Read/write notification snapshots to a JSON file."""

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
