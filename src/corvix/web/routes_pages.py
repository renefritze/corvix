"""Page routes: SPA shell serving, login form, and session cookie issuing."""

from __future__ import annotations

import hmac
from typing import Any

from litestar import Request, Response, get, post
from litestar.datastructures.cookie import Cookie
from litestar.exceptions import HTTPException
from litestar.response.redirect import Redirect

from corvix.web.assets import _MEDIA_TYPE_HTML, INDEX_HTML
from corvix.web.middleware import SESSION_MAX_AGE_SECONDS, _get_secret, _make_session_cookie

_LOGIN_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Corvix — Sign in</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, sans-serif;
      display: flex; height: 100vh;
      align-items: center; justify-content: center;
      background: #07111f; color: #edf3ff;
    }
    form {
      display: flex; flex-direction: column; gap: 1rem;
      min-width: 300px; padding: 2rem;
      background: #0e1a2b; border-radius: 8px;
    }
    h2 { font-size: 1.4rem; color: #74c0fc; }
    input[type=password] {
      padding: .65rem .9rem; border-radius: 6px;
      border: 1px solid #223753; background: #132238;
      color: #edf3ff; font-size: 1rem;
    }
    input[type=password]:focus { outline: 2px solid #74c0fc; border-color: transparent; }
    button {
      padding: .65rem .9rem; border-radius: 6px; border: none;
      background: #74c0fc; color: #07111f;
      font-size: 1rem; font-weight: 600; cursor: pointer;
    }
    button:hover { background: #a5d4ff; }
  </style>
</head>
<body>
  <form method="post" action="/login">
    <h2>Corvix</h2>
    <input type="password" name="token" placeholder="Secret token" required autofocus>
    <button type="submit">Sign in</button>
  </form>
</body>
</html>"""


@get("/", sync_to_thread=False)
def index() -> Response[str]:
    """Serve the dashboard single-page UI."""
    return Response(content=INDEX_HTML, media_type=_MEDIA_TYPE_HTML)


@get("/dashboards/{dashboard_name:str}", sync_to_thread=False)
def dashboard_index(dashboard_name: str) -> Response[str]:
    """Serve the dashboard SPA for bookmarkable dashboard URLs."""
    del dashboard_name
    return Response(content=INDEX_HTML, media_type=_MEDIA_TYPE_HTML)


def _get_auth_secret() -> str:
    """Return the configured secret, delegating to middleware._get_secret().

    Using the shared implementation ensures consistent TTL caching, memoized
    misconfiguration logging, and ``_FILE`` support in one place.
    """
    return _get_secret()


@get("/login", sync_to_thread=False)
def login_page() -> Response[Any]:
    """Serve the login form, or redirect to / when auth is not configured."""
    if not _get_auth_secret():
        return Redirect("/")
    return Response(content=_LOGIN_HTML, media_type=_MEDIA_TYPE_HTML)


@post("/login")
async def login(request: Request) -> Response[None]:
    """Validate the submitted token and issue a session cookie on success.

    The ``Secure`` attribute is set when the request arrived over HTTPS.
    The scheme is read from ``request.url.scheme`` which reflects the real
    protocol when uvicorn is started with ``--proxy-headers`` (trusting
    ``X-Forwarded-Proto`` from a reverse proxy).  This avoids raw header
    inspection from application code, which can be spoofed by untrusted
    clients not behind a proxy.
    """
    form_data = await request.form()
    token = str(form_data.get("token", ""))
    secret = _get_auth_secret()
    if not secret or not hmac.compare_digest(token, secret):
        raise HTTPException(status_code=401, detail="Invalid token")
    session_val = _make_session_cookie(secret)
    redirect: Response[None] = Redirect("/")
    redirect.set_cookie(
        Cookie(
            key="corvix_session",
            value=session_val,
            httponly=True,
            samesite="strict",
            path="/",
            max_age=SESSION_MAX_AGE_SECONDS,
            secure=request.url.scheme == "https",
        )
    )
    return redirect


@get("/logout", sync_to_thread=False)
def logout() -> Response[None]:
    """Clear the session cookie and redirect to the login page."""
    redirect: Response[None] = Redirect("/login")
    redirect.delete_cookie("corvix_session")
    return redirect
