#!/usr/bin/env bash
set -euo pipefail

echo "==> Stopping containers and removing volumes ..."
docker compose down --volumes

echo "==> Removing local cache ..."
rm -f ~/.cache/corvix/notifications.json

echo "==> Done. State fully reset."
