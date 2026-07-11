"""Token-based authentication middleware for the Corvix web app.

When ``CORVIX_SECRET_TOKEN`` (or ``CORVIX_SECRET_TOKEN_FILE``) is set:

* ``/api/*`` routes (except ``/api/health``) and ``/metrics`` require an
  ``Authorization: Bearer <token>`` or ``X-Corvix-Token: <token>`` header,
  **or** a valid ``corvix_session`` cookie (so the browser SPA works after
  logging in via the web UI without needing to inject headers; Prometheus
  scrape configs use the bearer-token form).
* UI routes (``/``, ``/dashboards/*``) require a ``corvix_session`` cookie;
  requests without a valid cookie are redirected to ``/login``.
* ``/api/health``, ``/assets/*``, ``/login``, and ``/logout`` are always public.

When the environment variable is *not* set, the middleware is a no-op and the
app behaves exactly as before (backward compatible).

Fail-closed misconfiguration
-----------------------------
If both ``CORVIX_SECRET_TOKEN`` and ``CORVIX_SECRET_TOKEN_FILE`` are set,
:func:`corvix.env.get_env_value` cannot determine which one wins.  This is
treated as a hard misconfiguration, never as "auth disabled": the app
refuses to start (see ``_validate_secret_config`` in ``corvix.web.app``),
and as defense in depth this middleware also rejects every non-public
request with ``500`` instead of passing it through.

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
# Both the versioned (/api/v1/health) and the deprecated (/api/health) health
# endpoints are always public so container health checks never need credentials.
# ``/metrics`` is deliberately NOT here: when auth is enabled it requires the
# same Bearer/X-Corvix-Token credentials as ``/api/*`` (see ``TokenAuthMiddleware``),
# since it exposes route templates and request counts (issue #131).
_PUBLIC_EXACT: frozenset[str] = frozenset({"/api/health", "/api/v1/health", "/login", "/logout", "/assets"})
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
    jar: SimpleCookie = SimpleCookie()
    jar.load(cookie_header)
    return {k: v.value for k, v in jar.items()}


# ---------------------------------------------------------------------------
# Secret resolution with TTL cache
# ---------------------------------------------------------------------------


class SecretConfigError(RuntimeError):
    """Raised when CORVIX_SECRET_TOKEN and CORVIX_SECRET_TOKEN_FILE are both set."""


_MISCONFIGURED_MESSAGE = (
    "CORVIX_SECRET_TOKEN misconfigured: both CORVIX_SECRET_TOKEN and "
    "CORVIX_SECRET_TOKEN_FILE are set. Refusing to authenticate requests "
    "(fail closed) until this is resolved."
)

_MISCONFIGURED: bool = False
_SECRET_CACHE: tuple[float, str] | None = None
_SECRET_CACHE_TTL: float = 60.0  # seconds
_MISCONFIGURED_UNTIL: float = 0.0


def _get_secret() -> str:
    """Return the configured secret token, or an empty string if not set.

    Results are cached for ``_SECRET_CACHE_TTL`` seconds so that deployments
    using ``CORVIX_SECRET_TOKEN_FILE`` do not incur a synchronous disk read on
    every request.  A configuration change takes effect within one TTL window.

    Raises:
        SecretConfigError: when both ``CORVIX_SECRET_TOKEN`` and
        ``CORVIX_SECRET_TOKEN_FILE`` are set. This is a hard failure — callers
        must fail closed (deny the request) rather than treat it as "no auth
        configured". Logs an error *once* per process to avoid flooding logs
        under load; the misconfigured state is itself cached for the TTL so
        repeated requests do not re-read the environment.
    """
    global _MISCONFIGURED, _SECRET_CACHE, _MISCONFIGURED_UNTIL  # noqa: PLW0603

    now = time.monotonic()
    if now < _MISCONFIGURED_UNTIL:
        raise SecretConfigError(_MISCONFIGURED_MESSAGE)
    if _SECRET_CACHE is not None and now - _SECRET_CACHE[0] < _SECRET_CACHE_TTL:
        return _SECRET_CACHE[1]

    try:
        value = get_env_value("CORVIX_SECRET_TOKEN") or ""
    except ValueError:
        if not _MISCONFIGURED:
            logger.error(_MISCONFIGURED_MESSAGE)
            _MISCONFIGURED = True
        _SECRET_CACHE = None
        _MISCONFIGURED_UNTIL = now + _SECRET_CACHE_TTL
        raise SecretConfigError(_MISCONFIGURED_MESSAGE) from None

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


_ASGI_RESPONSE_START = "http.response.start"
_ASGI_RESPONSE_BODY = "http.response.body"


async def _send_asgi_response(send: Send, status: int, body: bytes, headers: list[tuple[bytes, bytes]]) -> None:
    """Send a complete ASGI HTTP response (start + body events)."""
    await send(
        {
            "type": _ASGI_RESPONSE_START,
            "status": status,
            "headers": [*headers, (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": _ASGI_RESPONSE_BODY, "body": body, "more_body": False})


async def _send_json_401(send: Send) -> None:
    """Send a minimal JSON 401 Unauthorized response via ASGI."""
    await _send_asgi_response(
        send,
        401,
        b'{"detail":"Unauthorized"}',
        [
            (b"content-type", b"application/json"),
            (b"www-authenticate", b'Bearer realm="Corvix"'),
        ],
    )


async def _send_json_500(send: Send) -> None:
    """Send a minimal JSON 500 response for a misconfigured secret (fail closed)."""
    await _send_asgi_response(
        send,
        500,
        b'{"detail":"Server misconfigured: authentication secret is invalid"}',
        [(b"content-type", b"application/json")],
    )


async def _send_redirect(send: Send, location: bytes) -> None:
    """Send a 302 redirect response via ASGI."""
    await _send_asgi_response(send, 302, b"", [(b"location", location)])


# ---------------------------------------------------------------------------
# Request header helpers
# ---------------------------------------------------------------------------


def _parse_request_headers(scope: Scope) -> dict[bytes, bytes]:
    """Extract and normalise HTTP headers from an ASGI scope.

    RFC 7230 §3.2.4: header field values are ISO-8859-1 (latin-1); using
    latin-1 decoding (rather than strict UTF-8) means malformed byte sequences
    never raise :exc:`UnicodeDecodeError` and produce a clean 401/redirect
    instead of a 500.

    RFC 6265 §5.4: a request may carry multiple ``Cookie`` headers; they must
    be treated as if joined by ``"; "``.  A plain dict comprehension would
    silently drop all but the last occurrence, so Cookie header bytes are
    accumulated separately and joined before being stored.
    """
    raw_headers: dict[bytes, bytes] = {}
    cookie_parts: list[bytes] = []
    for k, v in scope.get("headers", []):
        k_lower = k.lower()
        if k_lower == b"cookie":
            cookie_parts.append(v)
        else:
            raw_headers[k_lower] = v
    if cookie_parts:
        raw_headers[b"cookie"] = b"; ".join(cookie_parts)
    return raw_headers


def _check_api_auth(raw_headers: dict[bytes, bytes], secret: str) -> bool:
    """Return True when the request carries valid API credentials.

    Checks ``Authorization: Bearer`` and ``X-Corvix-Token`` headers first
    (programmatic clients, curl, etc.).  Falls back to the ``corvix_session``
    cookie so browser SPAs work after logging in via the web UI without
    needing to inject custom headers into every ``fetch()`` call.
    """
    auth_header = raw_headers.get(b"authorization", b"").decode("latin-1")
    token_header = raw_headers.get(b"x-corvix-token", b"").decode("latin-1")

    provided_token = ""
    if auth_header.lower().startswith("bearer "):
        provided_token = auth_header[7:].strip()
    elif token_header:
        provided_token = token_header.strip()

    if provided_token:
        # Explicit header auth — constant-time comparison prevents timing leaks.
        return hmac.compare_digest(provided_token, secret)

    # Cookie fallback (browser SPA path).
    cookie_header = raw_headers.get(b"cookie", b"").decode("latin-1")
    session_val = _parse_cookies(cookie_header).get(_SESSION_COOKIE_NAME, "")
    return _verify_session_cookie(secret, session_val)


def _check_ui_auth(raw_headers: dict[bytes, bytes], secret: str) -> bool:
    """Return True when the request carries a valid ``corvix_session`` cookie."""
    cookie_header = raw_headers.get(b"cookie", b"").decode("latin-1")
    session_val = _parse_cookies(cookie_header).get(_SESSION_COOKIE_NAME, "")
    return _verify_session_cookie(secret, session_val)


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
        path: str = scope["path"]

        if _is_public(path):
            await next_app(scope, receive, send)
            return

        try:
            secret = _get_secret()
        except SecretConfigError:
            # Fail closed: a misconfigured secret must never be treated as
            # "auth disabled" for a route that isn't already public.
            await _send_json_500(send)
            return

        if not secret:
            await next_app(scope, receive, send)
            return

        raw_headers = _parse_request_headers(scope)

        if path.startswith("/api/") or path == "/metrics":
            # ----- API routes (+ /metrics): Bearer/X-Corvix-Token header OR session cookie -----
            if not _check_api_auth(raw_headers, secret):
                await _send_json_401(send)
                return
        elif not _check_ui_auth(raw_headers, secret):
            # ----- UI routes: session cookie; redirect to login if absent/invalid -----
            await _send_redirect(send, b"/login")
            return

        await next_app(scope, receive, send)
