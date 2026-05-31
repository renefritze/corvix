#!/usr/bin/env python3
"""Export the Litestar OpenAPI document to ``frontend/openapi.json``.

The Litestar app auto-generates an OpenAPI schema from the typed route-handler
return annotations (see ``corvix.web.schemas``). This script renders that schema
to a stable, pretty-printed JSON file that is committed to the repository and
used to code-generate the frontend's TypeScript types via ``openapi-typescript``.

Run it (together with the TypeScript generation step) with::

    make gen-types

The committed output is drift-checked in CI: any backend schema change that is
not regenerated here fails the build.
"""

from __future__ import annotations

import json
from pathlib import Path

from corvix.web.app import app

_REPO_ROOT = Path(__file__).resolve().parent.parent
_OUTPUT_PATH = _REPO_ROOT / "frontend" / "openapi.json"


def _mark_all_properties_required(schema: dict[str, object]) -> None:
    """Force every ``*Response`` component schema to require all its properties.

    The Corvix response dataclasses (``corvix.web.schemas``) define no field
    defaults, so the API always emits every key — nullable fields are present
    with a ``null`` value, never omitted. Litestar, following a common OpenAPI
    convention, leaves nullable (``T | None``) fields out of ``required``, which
    would make the code-generated TypeScript properties optional and diverge
    from the actual wire contract. Re-adding them keeps the generated types
    faithful: every field present, nullable ones typed ``T | null``.

    Scoped to schemas whose name ends with ``Response`` so that any future
    request-body schema (where optional fields are legitimate) is left untouched.
    """
    components = schema.get("components")
    if not isinstance(components, dict):
        return
    schemas = components.get("schemas")
    if not isinstance(schemas, dict):
        return
    for name, component in schemas.items():
        if not name.endswith("Response"):
            continue
        if not isinstance(component, dict) or component.get("type") != "object":
            continue
        properties = component.get("properties")
        if isinstance(properties, dict):
            component["required"] = sorted(properties)


def render_openapi() -> dict[str, object]:
    """Return the app's OpenAPI document as a plain JSON-serializable dict."""
    schema = app.openapi_schema.to_schema()
    # Round-trip through JSON so the in-memory schema (which may contain
    # tuples/enum members) is normalized to the exact structure that will be
    # written to disk and consumed by openapi-typescript.
    document: dict[str, object] = json.loads(json.dumps(schema, sort_keys=True))
    _mark_all_properties_required(document)
    return document


def main() -> None:
    """Write the OpenAPI document to ``frontend/openapi.json``."""
    document = render_openapi()
    serialized = json.dumps(document, indent=2, sort_keys=True) + "\n"
    _OUTPUT_PATH.write_text(serialized, encoding="utf-8")
    print(f"Wrote OpenAPI schema to {_OUTPUT_PATH.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
