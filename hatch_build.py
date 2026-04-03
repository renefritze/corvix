"""Hatch build hook for generating frontend assets."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    class BuildHookInterface:
        root: str

        def initialize(self, version: str, build_data: dict[str, object]) -> None: ...

else:
    try:
        BuildHookInterface = import_module(
            "hatchling.builders.hooks.plugin.interface",
        ).BuildHookInterface
    except ModuleNotFoundError:

        class BuildHookInterface:
            root: str


PLUGIN_NAME = "custom"


class CustomBuildHook(BuildHookInterface):
    """Build frontend assets before creating wheel/sdist."""

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        root = Path(self.root)
        assets_dir = root / "src" / "corvix" / "web" / "static" / "assets"
        if (assets_dir / "app.js").exists() and (assets_dir / "index.css").exists():
            return
        frontend_dir = root / "frontend"
        if not frontend_dir.exists():
            msg = f"Frontend directory not found: {frontend_dir}"
            raise RuntimeError(msg)
        try:
            run(["npm", "ci"], cwd=frontend_dir, check=True)
            run(["npm", "run", "build"], cwd=frontend_dir, check=True)
        except FileNotFoundError as error:
            msg = "npm is required to build frontend assets for packaging."
            raise RuntimeError(msg) from error
        except CalledProcessError as error:
            msg = f"Frontend build failed with exit code {error.returncode}."
            raise RuntimeError(msg) from error
