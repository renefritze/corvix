"""Exercise the Alembic migration chain itself against a real Postgres.

`test_storage_postgres.py` runs migrations to set up its schema, but only
implicitly -- it never checks that the resulting schema actually matches
`corvix.db`'s ORM metadata, nor that a downgrade actually reverses cleanly.
A migration that silently drifts from the ORM models (or a downgrade that
can't be undone) would otherwise only surface on a user's machine.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from corvix.db import Base

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"

# a1b2c3d4e5f6 drops tables it can't safely recreate, so its downgrade() is
# an intentional no-op -- round-tripping *that* revision would fail with
# "constraint already dropped" on re-upgrade. The current head sits on top
# of it and has a real, reversible downgrade, so that's what gets exercised
# here rather than walking all the way back down the chain.


@pytest.fixture()
def alembic_config(postgres_urls: tuple[str, str]) -> Generator[Config]:
    sqlalchemy_url, _ = postgres_urls
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = sqlalchemy_url
    try:
        yield Config(str(ALEMBIC_INI))
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url


@pytest.mark.integration
def test_upgrade_head_matches_orm_metadata(alembic_config: Config, postgres_urls: tuple[str, str]) -> None:
    """The schema `alembic upgrade head` produces must match `corvix.db`'s metadata.

    A mismatch here means a model changed without a matching migration (or
    vice versa) -- exactly the drift that otherwise ships silently.
    """
    sqlalchemy_url, _ = postgres_urls
    command.upgrade(alembic_config, "head")

    engine = sa.create_engine(sqlalchemy_url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            diff = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert diff == [], f"Migrations are out of sync with corvix.db metadata: {diff}"


@pytest.mark.integration
def test_downgrade_and_reupgrade_head(alembic_config: Config) -> None:
    """The newest migration's downgrade should cleanly reverse and re-apply."""
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "-1")
    command.upgrade(alembic_config, "head")
