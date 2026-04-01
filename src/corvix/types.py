"""Shared type aliases used across Corvix modules."""

from __future__ import annotations

from uuid import UUID

type UserId = str | UUID

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | JsonObject | JsonArray
type JsonObject = dict[str, JsonValue]
type JsonArray = list[JsonValue]
