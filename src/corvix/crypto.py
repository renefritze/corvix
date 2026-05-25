"""Fernet-based token encryption helpers and SQLAlchemy encrypted column type."""

from __future__ import annotations

from functools import cache

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from corvix.env import get_env_value


@cache
def get_fernet() -> Fernet:
    """Return a Fernet instance keyed from the TOKEN_ENCRYPTION_KEY env var.

    Raises:
        RuntimeError: if TOKEN_ENCRYPTION_KEY (or TOKEN_ENCRYPTION_KEY_FILE) is not set.
    """
    key = get_env_value("TOKEN_ENCRYPTION_KEY")
    if not key:
        msg = (
            "TOKEN_ENCRYPTION_KEY environment variable is required for token encryption. "
            "Generate a key with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
        raise RuntimeError(msg)
    return Fernet(key.encode())


def encrypt_token(plaintext: str) -> str:
    """Encrypt a plaintext token string with Fernet symmetric encryption.

    Returns:
        A URL-safe base64-encoded Fernet token (starts with ``gAAAAA``).
    """
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted token string back to plaintext.

    Raises:
        cryptography.fernet.InvalidToken: if the ciphertext is invalid or the key is wrong.
    """
    return get_fernet().decrypt(ciphertext.encode()).decode()


class EncryptedText(TypeDecorator):
    """SQLAlchemy column type that transparently Fernet-encrypts values at rest.

    The database column stores a URL-safe base64 Fernet token (plain TEXT).
    Python code reads and writes the original plaintext string.

    Requires the TOKEN_ENCRYPTION_KEY environment variable (or TOKEN_ENCRYPTION_KEY_FILE
    for Docker secret file support) to be set at application startup and during migrations.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: object) -> str | None:  # noqa: ANN001
        """Encrypt the Python value before writing it to the database."""
        if value is None:
            return None
        return encrypt_token(value)

    def process_result_value(self, value: str | None, dialect: object) -> str | None:  # noqa: ANN001
        """Decrypt the database value when loading it into Python."""
        if value is None:
            return None
        return decrypt_token(value)


__all__ = ["EncryptedText", "InvalidToken", "decrypt_token", "encrypt_token", "get_fernet"]
