"""encrypt_existing_github_tokens

Revision ID: c3a1f2e9b8d0
Revises: 6d0e5f9d2a1b
Create Date: 2026-05-25

"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from cryptography.fernet import Fernet, InvalidToken

revision: str = "c3a1f2e9b8d0"
down_revision: str | None = "6d0e5f9d2a1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _get_fernet() -> Fernet:
    """Return a Fernet instance from TOKEN_ENCRYPTION_KEY env var."""
    key = os.environ.get("TOKEN_ENCRYPTION_KEY")
    if not key:
        # Also support Docker secret file convention handled by get_env_value,
        # but avoid importing application code in migrations to keep them self-contained.
        key_file = os.environ.get("TOKEN_ENCRYPTION_KEY_FILE")
        if key_file:
            from pathlib import Path  # noqa: PLC0415

            key = Path(key_file).read_text(encoding="utf-8").strip()
    if not key:
        msg = (
            "TOKEN_ENCRYPTION_KEY environment variable must be set to run this migration. "
            "Generate a key with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
        raise RuntimeError(msg)
    return Fernet(key.encode())


def upgrade() -> None:
    """Encrypt any existing plaintext github_token values in the users table."""
    fernet = _get_fernet()
    conn = op.get_bind()

    # Iterate without fetchall() to avoid loading all rows into memory at once.
    for row in conn.execute(sa.text("SELECT id, github_token FROM users")):
        user_id, token = row
        if not token:
            continue
        # Fernet ciphertext always starts with the version byte 0x80, which
        # encodes to "gAAAAA" in URL-safe base64.
        if token.startswith("gAAAAA"):
            # Token looks already encrypted — verify it decrypts with the
            # current key so we catch a mismatched TOKEN_ENCRYPTION_KEY early
            # rather than leaving the database in a partially-migrated state.
            try:
                fernet.decrypt(token.encode())
            except InvalidToken:
                msg = (
                    f"Token for user {user_id} appears already encrypted but "
                    "decryption failed with the current TOKEN_ENCRYPTION_KEY. "
                    "Ensure the key matches the one used to encrypt existing tokens."
                )
                raise RuntimeError(msg) from None
            # Already encrypted with the current key — nothing to do.
            continue
        encrypted = fernet.encrypt(token.encode()).decode()
        conn.execute(
            sa.text("UPDATE users SET github_token = :token WHERE id = :id"),
            {"token": encrypted, "id": str(user_id)},
        )


def downgrade() -> None:
    """No-op: encrypted tokens cannot be safely reversed to plaintext.

    To restore plaintext storage you would need to decrypt all values with the
    current key and change the application code back — doing so automatically
    would re-introduce the security vulnerability this migration was written
    to fix.
    """
