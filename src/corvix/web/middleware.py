"""Token-based authentication middleware for the Corvix web app.

When ``CORVIX_SECRET_TOKEN`` (or ``CORVIX_SECRET_TOKEN_FILE``) is set:

* ``/api/*`` routes (except ``/api/health``) require an
  ``Authorization: Bearer <token>`` or ``X-Corvix-Token: <token>`` header,
  **or** a valid ``corvix_session`` cookie (so the browser SPA works after
  logging in via the web UI without needing to inject headers).
* UI routes (``/``, ``/dashboards/*``) require a ``corvix_session`` cookie;
  requests without a valid cookie are redirected to ``/login``.
* ``/api/health``, ``/assets/*``, ``/login``, and ``/logout`` are always public.

When the environment variable is *not* set, the middleware is a no-op and the
app behaves exactly as before (backward compatible).

HTTPS detection
---------------
The ``corvix_session`` cookie is marked ``Secure`` only when the request
arrives over HTTPS.  The scheme is read from ``request.url.scheme``, which
reflects the real protocol when uvicorn is started with ``--proxy-headers``
(trusting ``X-Forwarded-Proto`` from a reverse proxy).  Without that flag,
direct HTTPS connections are still detected correctly via the connection
scheme.  Do **not** rely on raw ``X-Forwarded-Proto`` header inspection from
application code: untrusted clients can spoof it.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from http.cookies import SimpleCookie
from typing import TYPE_CHECKING

from litestar.enums import ScopeType
from litestar.middleware.base import ASGIMiddleware

from corvix.env import get_env_value

if TYPE_CHECKING:
    from litestar.types.asgi_types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

_SESSION_COOKIE_NAME = "corvix_session"

# Session cookie lifetime.  The cookie both carries its own expiry (verified
# server-side) and sets max-age so browsers expire it promptly.
SESSION_MAX_AGE_SECONDS: int = 24 * 60 * 60  # 24 hours

# Paths that are always accessible without authentication.
# /assets (exact) handles the bare mount request; /assets/ handles static
# file requests.  Using exact + trailing-slash prefix avoids accidentally
# making unrelated paths like /assets-private/ public.
_PUBLIC_EXACT: frozenset[str] = frozenset({"/api/health", "/login", "/logout", "/assets"})
_PUBLIC_PREFIXES: tuple[str, ...] = ("/assets/",)

# ---------------------------------------------------------------------------
# Session cookie helpers
# ---------------------------------------------------------------------------


def _make_session_cookie(secret: str) -> str:
    """Return a signed, time-limited session cookie value.

    Format: ``{expiry_unix_timestamp}:{hmac_sha256_hex}``

    The HMAC covers both the fixed context string and the expiry timestamp so
    that the expiry cannot be extended without knowing the secret.
    """
    expiry = int(time.time()) + SESSION_MAX_AGE_SECONDS
    msg = f"corvix-session-v2:{expiry}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"{expiry}:{sig}"


def _verify_session_cookie(secret: str, value: str) -> bool:
    """Return True when *value* is a valid, unexpired session token.

    Validates the HMAC signature and rejects tokens whose expiry timestamp is
    in the past.  Uses :func:`hmac.compare_digest` to prevent timing attacks.
    """
    try:
        expiry_str, sig = value.split(":", 1)
        expiry = int(expiry_str)
    except ValueError:
        return False

    if time.time() > expiry:
        return False

    msg = f"corvix-session-v2:{expiry}".encode()
    expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


# ---------------------------------------------------------------------------
# Cookie parsing
# ---------------------------------------------------------------------------


def _parse_cookies(cookie_header: str) -> dict[str, str]:
    """Parse a raw ``Cookie`` header value into a name→value dict.

    Uses :class:`http.cookies.SimpleCookie` from the standard library to
    handle quoted values and other edge cases correctly.
    """
    jar: SimpleCookie[str] = SimpleCookie()
    jar.load(cookie_header)
    return {k: v.value for k, v in jar.items()}


# ---------------------------------------------------------------------------
# Secret resolution with TTL cache
# ---------------------------------------------------------------------------

_MISCONFIGURED: bool = False
_SECRET_CACHE: tuple[float, str] | None = None
_SECRET_CACHE_TTL: float = 60.0  # seconds


def _get_secret() -> str:
    """Return the configured secret token, or an empty string if not set.

    Results are cached for ``_SECRET_CACHE_TTL`` seconds so that deployments
    using ``CORVIX_SECRET_TOKEN_FILE`` do not incur a synchronous disk read on
    every request.  A configuration change takes effect within one TTL window.

    When both ``CORVIX_SECRET_TOKEN`` and ``CORVIX_SECRET_TOKEN_FILE`` are set
    simultaneously, logs a warning *once* per process and returns an empty
    string (auth disabled) to avoid flooding logs under load.
    """
    global _MISCONFIGURED, _SECRET_CACHE  # noqa: PLW0603

    now = time.monotonic()
    if _SECRET_CACHE is not None and now - _SECRET_CACHE[0] < _SECRET_CACHE_TTL:
        return _SECRET_CACHE[1]

    try:
        value = get_env_value("CORVIX_SECRET_TOKEN") or ""
    except ValueError:
        if not _MISCONFIGURED:
            logger.warning(
                "CORVIX_SECRET_TOKEN misconfigured (both direct and _FILE set); auth disabled."
            )
            _MISCONFIGURED = True
        value = ""

    _SECRET_CACHE = (now, value)
    return value


# ---------------------------------------------------------------------------
# Public-path check
# ---------------------------------------------------------------------------


def _is_public(path: str) -> bool:
    """Return True when *path* should never require authentication."""
    if path in _PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


# ---------------------------------------------------------------------------
# ASGI response helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class TokenAuthMiddleware(ASGIMiddleware):
    """Optional token-based authentication middleware.

    Reads the secret from ``CORVIX_SECRET_TOKEN`` (or ``CORVIX_SECRET_TOKEN_FILE``)
    with a 60-second TTL cache so that config changes take effect without a
    restart while avoiding per-request file I/O.
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
        # RFC 7230 §3.2.4: header field values are ISO-8859-1 (latin-1).
        # Using latin-1 (rather than the default strict UTF-8) means malformed
        # byte sequences never raise UnicodeDecodeError and produce a clean
        # 401/redirect instead of a 500.
        raw_headers: dict[bytes, bytes] = {k.lower(): v for k, v in scope.get("headers", [])}

        def _decode(b: bytes) -> str:
            return b.decode("latin-1")

        if path.startswith("/api/"):
            # ----- API routes: Bearer/X-Corvix-Token header OR session cookie -----
            # Headers are checked first (programmatic clients, curl, etc.).
            # Cookie fallback lets the browser SPA work after a /login without
            # needing to inject custom headers into every fetch() call.
            auth_header = _decode(raw_headers.get(b"authorization", b""))
            token_header = _decode(raw_headers.get(b"x-corvix-token", b""))

            provided_token = ""
            if auth_header.lower().startswith("bearer "):
                provided_token = auth_header[7:].strip()
            elif token_header:
                provided_token = token_header.strip()

            if provided_token:
                # Explicit header auth.
                if not hmac.compare_digest(provided_token, secret):
                    await _send_json_401(send)
                    return
            else:
                # Cookie fallback (browser SPA path).
                cookie_header = _decode(raw_headers.get(b"cookie", b""))
                session_val = _parse_cookies(cookie_header).get(_SESSION_COOKIE_NAME, "")
                if not _verify_session_cookie(secret, session_val):
                    await _send_json_401(send)
                    return

        else:
            # ----- UI routes: session cookie -----
            cookie_header = _decode(raw_headers.get(b"cookie", b""))
            session_val = _parse_cookies(cookie_header).get(_SESSION_COOKIE_NAME, "")

            if not _verify_session_cookie(secret, session_val):
                await _send_redirect(send, b"/login")
                return

        await next_app(scope, receive, send)
