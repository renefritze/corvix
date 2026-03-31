"""Makes sure all our fixtures are available to all tests

Individual test modules MUST NOT import fixtures from `tests.fixtures`,
as this can have strange side effects.
"""

from importlib.resources import files as resource_files

import pytest

pytest_plugins = [
    "tests.fixtures",
]


def pytest_sessionstart(session: pytest.Session) -> None:
    """Fail early if frontend build artifacts are missing."""
    assets = resource_files("corvix.web").joinpath("static/assets")
    missing = [name for name in ("app.js", "index.css") if not assets.joinpath(name).is_file()]
    if missing:
        joined = ", ".join(missing)
        msg = f"Missing frontend assets ({joined}). Run `make frontend-build` before `pytest`."
        raise pytest.UsageError(msg)
