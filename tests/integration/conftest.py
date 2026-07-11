"""Shared fixtures for Postgres-backed integration tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest


@pytest.fixture(scope="session")
def postgres_urls() -> Generator[tuple[str, str]]:
    """Start a fresh, unmigrated Postgres container for the test session."""
    testcontainers = pytest.importorskip("testcontainers.postgres")
    try:
        container = testcontainers.PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as error:  # pragma: no cover - environment dependent
        pytest.skip(f"Could not start Postgres test container: {error}")
    try:
        raw_url = container.get_connection_url()
        sqlalchemy_url = raw_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        psycopg_url = raw_url.replace("postgresql+psycopg2://", "postgresql://", 1)
        yield sqlalchemy_url, psycopg_url
    finally:
        container.stop()
