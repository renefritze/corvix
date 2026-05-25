"""Makes sure all our fixtures are available to all tests

Individual test modules MUST NOT import fixtures from `tests.fixtures`,
as this can have strange side effects.
"""

from collections.abc import Generator
from importlib.resources import files as resource_files

import pytest

import corvix.web.app as _web_app

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


@pytest.fixture(autouse=True)
def _reset_runtime_config_cache() -> Generator[None]:
    """Clear the module-level runtime-config cache before and after every test.

    ``_load_runtime_config()`` caches the parsed ``AppConfig`` at module level.
    Without resetting the cache between tests, a config loaded in one test can
    bleed into subsequent tests that use a different ``CORVIX_CONFIG`` path,
    causing spurious passes or failures.
    """
    _web_app._clear_config_cache()
    yield
    _web_app._clear_config_cache()
