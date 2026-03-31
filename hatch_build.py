"""Hatch build hook for generating frontend assets."""

from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError, run

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

PLUGIN_NAME = "custom"


class CustomBuildHook(BuildHookInterface):
    """Build frontend assets before creating wheel/sdist."""

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        root = Path(self.root)
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
