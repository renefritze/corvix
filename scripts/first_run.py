#!/usr/bin/env python3
"""First-time local init helper for config and Docker secret files."""

from __future__ import annotations

import secrets
import string
import subprocess
from pathlib import Path

SECRETS_DIR = Path("secrets")
CONFIG_DIR = Path("config")
POSTGRES_PASSWORD_FILE = SECRETS_DIR / "postgres_password.txt"
DATABASE_URL_FILE = SECRETS_DIR / "database_url.txt"
GITHUB_TOKEN_FILE = SECRETS_DIR / "github_token.txt"
CONFIG_EXAMPLE_FILE = CONFIG_DIR / "corvix.example.yaml"
CONFIG_FILE = CONFIG_DIR / "corvix.yaml"


def _random_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _gh_auth_token() -> str:
    result = subprocess.run(["gh", "auth", "token"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown error"
        msg = f"`gh auth token` failed: {stderr}"
        raise RuntimeError(msg)
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("`gh auth token` returned an empty value")
    return token


def _docker_login() -> None:
    try:
        subprocess.run(["docker", "login"], check=True)
    except subprocess.CalledProcessError as error:
        msg = f"`docker login` failed with exit code {error.returncode}"
        raise RuntimeError(msg) from error


def main() -> int:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _docker_login()

    if not CONFIG_FILE.exists():
        if not CONFIG_EXAMPLE_FILE.exists():
            msg = f"Missing template config file: {CONFIG_EXAMPLE_FILE}"
            raise RuntimeError(msg)
        CONFIG_FILE.write_text(CONFIG_EXAMPLE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Wrote {CONFIG_FILE}")
    else:
        print(f"Skipped existing {CONFIG_FILE}")

    if POSTGRES_PASSWORD_FILE.exists():
        db_password = POSTGRES_PASSWORD_FILE.read_text(encoding="utf-8").strip()
        if not db_password:
            msg = f"Existing file is empty: {POSTGRES_PASSWORD_FILE}"
            raise RuntimeError(msg)
        print(f"Skipped existing {POSTGRES_PASSWORD_FILE}")
    else:
        db_password = _random_password()
        POSTGRES_PASSWORD_FILE.write_text(f"{db_password}\n", encoding="utf-8")
        print(f"Wrote {POSTGRES_PASSWORD_FILE}")

    if DATABASE_URL_FILE.exists():
        print(f"Skipped existing {DATABASE_URL_FILE}")
    else:
        db_url = f"postgresql://corvix:{db_password}@db:5432/corvix"
        DATABASE_URL_FILE.write_text(f"{db_url}\n", encoding="utf-8")
        print(f"Wrote {DATABASE_URL_FILE}")

    if GITHUB_TOKEN_FILE.exists():
        print(f"Skipped existing {GITHUB_TOKEN_FILE}")
    else:
        gh_token = _gh_auth_token()
        GITHUB_TOKEN_FILE.write_text(f"{gh_token}\n", encoding="utf-8")
        print(f"Wrote {GITHUB_TOKEN_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
