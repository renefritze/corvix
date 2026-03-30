"""Environment variable helpers, including Docker secret file support."""

from __future__ import annotations

from os import environ
from pathlib import Path


def get_env_value(name: str) -> str | None:
    """Return env var value, supporting `${NAME}_FILE` secret file fallbacks.

    Resolution order:
    1) `${NAME}` if set and non-empty
    2) file contents from `${NAME}_FILE` if set and non-empty
    3) `None` when neither is provided

    Raises:
        ValueError: if both `${NAME}` and `${NAME}_FILE` are set, or if the file
        path is unreadable.
    """

    direct = environ.get(name)
    file_path = environ.get(f"{name}_FILE")

    if direct and file_path:
        msg = f"Both '{name}' and '{name}_FILE' are set; use only one."
        raise ValueError(msg)

    if direct:
        return direct

    if not file_path:
        return None

    try:
        return Path(file_path).read_text(encoding="utf-8").strip()
    except OSError as error:
        msg = f"Failed to read secret file from '{name}_FILE': {error}"
        raise ValueError(msg) from error
