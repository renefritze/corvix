"""Token-based authentication middleware for the Corvix web app.

When ``CORVIX_SECRET_TOKEN`` (or ``CORVIX_SECRET_TOKEN_FILE``) is set:

* ``/api/*`` routes (except ``/api/health``) require an
  ``Authorization: Bearer <token>`` or ``X-Corvix-Token: <token>`` header.
* UI routes (``/``, ``/dashboards/*``) require a ``corvix_session`` cookie;
  requests without a valid cookie are redirected to ``/login``.
* ``/api/health``, ``/assets/*``, ``/login``, and ``/logout`` are always public.

When the environment variable is *not* set, the middleware is a no-op and the
app behaves exactly as before (backward compatible).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import TYPE_CHECKING

from litestar.enums import ScopeType
from litestar.middleware.base import ASGIMiddleware

from corvix.env import get_env_value

if TYPE_CHECKING:
    from litestar.types.asgi_types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

_SESSION_COOKIE_NAME = "corvix_session"
_SESSION_HMAC_MSG = b"corvix-session-v1"

# Paths that are always accessible without authentication.
_PUBLIC_EXACT: frozenset[str] = frozenset({"/api/health", "/login", "/logout"})
_PUBLIC_PREFIXES: tuple[str, ...] = ("/assets/",)


def _compute_session_token(secret: str) -> str:
    """Return a deterministic session token derived from *secret* via HMAC-SHA256.

    The same secret always produces the same token so no server-side session
    store is required.  The token is stored as a hex digest.
    """
    return hmac.new(secret.encode(), _SESSION_HMAC_MSG, hashlib.sha256).hexdigest()


def _parse_cookies(cookie_header: str) -> dict[str, str]:
    """Parse a raw ``Cookie`` header value into a name→value dict."""
    cookies: dict[str, str] = {}
    for raw_part in cookie_header.split(";"):
        stripped = raw_part.strip()
        if "=" in stripped:
            name, _, value = stripped.partition("=")
            cookies[name.strip()] = value.strip()
    return cookies


def _get_secret() -> str:
    """Return the configured secret token, or an empty string if not set."""
    try:
        return get_env_value("CORVIX_SECRET_TOKEN") or ""
    except ValueError:
        logger.warning("CORVIX_SECRET_TOKEN misconfigured (both direct and _FILE set); auth disabled.")
        return ""


def _is_public(path: str) -> bool:
    """Return True when *path* should never require authentication."""
    if path in _PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


async def _send_json_401(send: Send) -> None:
    """Send a minimal JSON 401 Unauthorized response via ASGI."""
    body = b'{"detail":"Unauthorized"}'
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"www-authenticate", b'Bearer realm="Corvix"'),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})


async def _send_redirect(send: Send, location: bytes) -> None:
    """Send a 302 redirect response via ASGI."""
    await send(
        {
            "type": "http.response.start",
            "status": 302,
            "headers": [
                (b"location", location),
                (b"content-length", b"0"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": b"", "more_body": False})


class TokenAuthMiddleware(ASGIMiddleware):
    """Optional token-based authentication middleware.

    Reads the secret from ``CORVIX_SECRET_TOKEN`` (or ``CORVIX_SECRET_TOKEN_FILE``)
    on every request so that config changes take effect without a restart.
    When the variable is absent the middleware is a transparent pass-through.
    """

    scopes = (ScopeType.HTTP,)

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        """Authenticate the request or pass it through."""
        secret = _get_secret()
        if not secret:
            await next_app(scope, receive, send)
            return

        path: str = scope["path"]

        if _is_public(path):
            await next_app(scope, receive, send)
            return

        # Parse headers once.
        raw_headers: dict[bytes, bytes] = {k.lower(): v for k, v in scope.get("headers", [])}

        if path.startswith("/api/"):
            # ----- API routes: Bearer or X-Corvix-Token header -----
            auth_header = raw_headers.get(b"authorization", b"").decode()
            token_header = raw_headers.get(b"x-corvix-token", b"").decode()

            provided = ""
            if auth_header.lower().startswith("bearer "):
                provided = auth_header[7:].strip()
            elif token_header:
                provided = token_header.strip()

            if not provided or not hmac.compare_digest(provided, secret):
                await _send_json_401(send)
                return

        else:
            # ----- UI routes: session cookie -----
            cookie_header = raw_headers.get(b"cookie", b"").decode()
            session_val = _parse_cookies(cookie_header).get(_SESSION_COOKIE_NAME, "")
            expected = _compute_session_token(secret)

            if not session_val or not hmac.compare_digest(session_val, expected):
                await _send_redirect(send, b"/login")
                return

        await next_app(scope, receive, send)
