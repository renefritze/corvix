"""Process-wide storage backend singleton for the web app.

Production wiring builds a PostgreSQL backend lazily from config on first use
and caches it so its connection pool is reused across requests.  Tests inject a
backend directly via :func:`set_storage_backend` and reset it to ``None``
afterwards.
"""

from __future__ import annotations

import threading

from litestar.exceptions import HTTPException

from corvix.storage import StorageBackend, StorageConfigError, create_storage
from corvix.web.runtime_config import _load_runtime_config


class _StorageState:
    """Mutable container for the module-level storage backend."""

    backend: StorageBackend | None = None
    lock: threading.Lock = threading.Lock()


_storage_state = _StorageState()


def set_storage_backend(backend: StorageBackend | None) -> None:
    """Inject the storage backend used by route handlers.

    Production wiring leaves this unset and the backend is built lazily from
    config (PostgreSQL is required). Tests inject a backend directly and reset
    it to ``None`` afterwards.
    """
    _storage_state.backend = backend


def _get_storage() -> StorageBackend:
    """Return the injected backend, or lazily build PostgreSQL storage from config.

    The built backend is cached so its connection pool is reused across
    requests. Building is guarded by a lock so concurrent first requests don't
    each create (and leak) a connection pool. Raises ``HTTPException`` (500)
    when no database is configured.
    """
    if _storage_state.backend is not None:
        return _storage_state.backend
    with _storage_state.lock:
        if _storage_state.backend is not None:
            return _storage_state.backend
        config = _load_runtime_config()
        try:
            backend = create_storage(config)
        except StorageConfigError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
        _storage_state.backend = backend
        return backend
