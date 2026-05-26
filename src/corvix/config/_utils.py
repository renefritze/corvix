"""Shared YAML parsing helpers."""

from __future__ import annotations


def _ensure_map(value: object, section: str) -> dict[str, object]:
    if not isinstance(value, dict):
        msg = f"Config section '{section}' must be a map/object."
        raise ValueError(msg)
    output: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            msg = f"Config section '{section}' must use string keys."
            raise ValueError(msg)
        output[key] = item
    return output


def _ensure_list(value: object, section: str) -> list[object]:
    if isinstance(value, list):
        return list(value)
    msg = f"Config section '{section}' must be a list."
    raise ValueError(msg)


def _as_bool(value: object, field: str) -> bool:
    if isinstance(value, bool):
        return value
    msg = f"Config field '{field}' must be a boolean."
    raise ValueError(msg)


def _as_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"Config field '{field}' must be an integer."
        raise ValueError(msg)
    return value


def _as_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"Config field '{field}' must be a number."
        raise ValueError(msg)
    return float(value)


def _as_str(value: object, field: str) -> str:
    if isinstance(value, str):
        return value
    msg = f"Config field '{field}' must be a string."
    raise ValueError(msg)


def _get_str(config: dict[str, object], key: str, default: str, field: str) -> str:
    if key not in config:
        return default
    return _as_str(config[key], field)


def _get_optional_str(config: dict[str, object], key: str, field: str) -> str | None:
    if key not in config or config[key] is None:
        return None
    return _as_str(config[key], field)


def _get_bool(config: dict[str, object], key: str, default: bool, field: str) -> bool:
    if key not in config:
        return default
    return _as_bool(config[key], field)


def _get_optional_bool(config: dict[str, object], key: str, field: str) -> bool | None:
    if key not in config or config[key] is None:
        return None
    return _as_bool(config[key], field)


def _get_int(config: dict[str, object], key: str, default: int, field: str) -> int:
    if key not in config:
        return default
    return _as_int(config[key], field)


def _get_float(config: dict[str, object], key: str, default: float, field: str) -> float:
    if key not in config:
        return default
    return _as_float(config[key], field)


def _get_optional_float(config: dict[str, object], key: str, field: str) -> float | None:
    if key not in config or config[key] is None:
        return None
    return _as_float(config[key], field)


def _to_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        msg = "Expected a list."
        raise ValueError(msg)
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            msg = "Expected a list of strings."
            raise ValueError(msg)
        output.append(item)
    return output


def _to_float_map(value: object, section: str) -> dict[str, float]:
    data = _ensure_map(value, section)
    return {key: _as_float(raw_value, f"{section}.{key}") for key, raw_value in data.items()}
