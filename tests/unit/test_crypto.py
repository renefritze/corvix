"""Unit tests for corvix.crypto — Fernet token encryption helpers."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken

from corvix.crypto import EncryptedText, decrypt_token, encrypt_token, get_fernet

_TEST_KEY = Fernet.generate_key().decode()
_PLAINTEXT = "ghp_some_github_personal_access_token"


@pytest.fixture(autouse=True)
def set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure TOKEN_ENCRYPTION_KEY is set for every test in this module.

    Also clears the get_fernet() cache so each test starts with a fresh
    Fernet instance keyed from the current environment.
    """
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", _TEST_KEY)
    get_fernet.cache_clear()
    yield
    # Teardown: clear the cache so tests in other modules are not affected.
    get_fernet.cache_clear()


# ---------------------------------------------------------------------------
# get_fernet
# ---------------------------------------------------------------------------


def test_get_fernet_returns_fernet_instance() -> None:
    f = get_fernet()
    assert isinstance(f, Fernet)


def test_get_fernet_raises_when_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY_FILE", raising=False)
    # The autouse fixture populated the cache with a valid key; clear it so the
    # env-var absence is visible to get_fernet().
    get_fernet.cache_clear()
    with pytest.raises(RuntimeError, match="TOKEN_ENCRYPTION_KEY"):
        get_fernet()


# ---------------------------------------------------------------------------
# encrypt_token / decrypt_token
# ---------------------------------------------------------------------------


def test_encrypt_token_returns_non_plaintext_string() -> None:
    ciphertext = encrypt_token(_PLAINTEXT)
    assert ciphertext != _PLAINTEXT
    # Fernet tokens are URL-safe base64 and start with "gAAAAA"
    assert ciphertext.startswith("gAAAAA")


def test_decrypt_token_round_trips() -> None:
    ciphertext = encrypt_token(_PLAINTEXT)
    assert decrypt_token(ciphertext) == _PLAINTEXT


def test_decrypt_token_raises_on_garbage_input() -> None:
    with pytest.raises(Exception):  # noqa: B017 — cryptography raises InvalidToken or binascii error
        decrypt_token("not-a-valid-fernet-token")


def test_encrypt_produces_different_ciphertext_each_call() -> None:
    """Fernet uses a random IV so two encryptions of the same value differ."""
    c1 = encrypt_token(_PLAINTEXT)
    c2 = encrypt_token(_PLAINTEXT)
    assert c1 != c2
    # Both decrypt to the same plaintext.
    assert decrypt_token(c1) == decrypt_token(c2) == _PLAINTEXT


# ---------------------------------------------------------------------------
# EncryptedText TypeDecorator
# ---------------------------------------------------------------------------


def test_encrypted_text_bind_param_encrypts() -> None:
    col_type = EncryptedText()
    result = col_type.process_bind_param(_PLAINTEXT, dialect=None)
    assert result is not None
    assert result != _PLAINTEXT
    assert result.startswith("gAAAAA")


def test_encrypted_text_result_value_decrypts() -> None:
    col_type = EncryptedText()
    ciphertext = encrypt_token(_PLAINTEXT)
    result = col_type.process_result_value(ciphertext, dialect=None)
    assert result == _PLAINTEXT


def test_encrypted_text_round_trip() -> None:
    col_type = EncryptedText()
    stored = col_type.process_bind_param(_PLAINTEXT, dialect=None)
    recovered = col_type.process_result_value(stored, dialect=None)
    assert recovered == _PLAINTEXT


def test_encrypted_text_bind_param_none_passthrough() -> None:
    col_type = EncryptedText()
    assert col_type.process_bind_param(None, dialect=None) is None


def test_encrypted_text_result_value_none_passthrough() -> None:
    col_type = EncryptedText()
    assert col_type.process_result_value(None, dialect=None) is None
