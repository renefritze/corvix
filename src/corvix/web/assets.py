"""Static asset resolution and the cached index.html body.

Owns the static-asset directory, the content-hash asset-version token, and the
rendered ``INDEX_HTML`` (the SPA shell with the version token substituted in).
Kept separate from the route handlers so both the page routes and the app
assembly can share these constants without importing route modules.
"""

from __future__ import annotations

import hashlib
from importlib.resources import files

from litestar.datastructures.headers import CacheControlHeader

_STATIC_ROOT = files("corvix.web").joinpath("static")
_STATIC_ASSETS_DIR = str(_STATIC_ROOT.joinpath("assets"))
_ASSET_FILENAMES = ("app.js", "index.css", "favicon.svg")
_ASSET_CACHE_CONTROL = CacheControlHeader(public=True, max_age=31536000, immutable=True)

_MEDIA_TYPE_HTML = "text/html"


def _asset_version_token() -> str:
    digest = hashlib.sha256()
    found_asset = False
    for asset_name in _ASSET_FILENAMES:
        asset_file = _STATIC_ROOT.joinpath("assets", asset_name)
        if not asset_file.is_file():
            continue
        found_asset = True
        digest.update(asset_name.encode("utf-8"))
        digest.update(asset_file.read_bytes())
    if not found_asset:
        return "dev"
    return digest.hexdigest()[:12]


_INDEX_HTML_TEMPLATE = _STATIC_ROOT.joinpath("index.html").read_text(encoding="utf-8")
INDEX_HTML = _INDEX_HTML_TEMPLATE.replace("__ASSET_VERSION__", _asset_version_token())
