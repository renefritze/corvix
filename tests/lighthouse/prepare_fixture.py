"""Seed the lighthouse smoke-test database from a static notifications template.

Reads the notifications template from ``$LH_TEMPLATE`` and upserts the records
into PostgreSQL (``$DATABASE_URL``) for the single-user identity, with a fresh
``poller_status`` so ``/api/health`` reports ``ok`` without a running poller.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from corvix.db import get_database_url
from corvix.domain import NotificationRecord, PollerStatus, format_timestamp
from corvix.storage import SINGLE_USER_ID, PostgresStorage


def main() -> int:
    template = Path(os.environ["LH_TEMPLATE"])  # NOSONAR: path set by docker-compose, not user input
    payload = json.loads(template.read_text(encoding="utf-8"))
    raw_notifications = payload.get("notifications", []) if isinstance(payload, dict) else []
    records = [NotificationRecord.from_dict(item) for item in raw_notifications if isinstance(item, dict)]

    db_url = get_database_url("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set; cannot seed lighthouse fixture.", file=sys.stderr)
        return 1

    now = datetime.now(tz=UTC)
    with PostgresStorage(connection_string=db_url) as storage:
        storage.save_records(SINGLE_USER_ID, records, now)
        storage.save_status(
            SINGLE_USER_ID,
            PollerStatus(
                status="ok",
                last_poll_time=format_timestamp(now),
                last_error=None,
                last_error_time=None,
            ),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
