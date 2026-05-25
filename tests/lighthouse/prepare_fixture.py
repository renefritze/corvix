"""Prepare a runtime cache fixture for the lighthouse smoke test.

Reads the static notifications template from ``$LH_TEMPLATE`` and writes a copy
to ``$LH_CACHE`` with ``poller_status`` populated with a current timestamp so
``/api/health`` reports ``ok`` without a running poller.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    template = Path(os.environ["LH_TEMPLATE"])  # NOSONAR: path set by docker-compose, not user input
    cache = Path(os.environ["LH_CACHE"])  # NOSONAR: path set by docker-compose, not user input
    payload = json.loads(template.read_text(encoding="utf-8"))
    now = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    payload["generated_at"] = now
    payload["poller_status"] = {
        "status": "ok",
        "last_poll_time": now,
        "last_error": None,
        "last_error_time": None,
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
