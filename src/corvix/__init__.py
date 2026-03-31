"""Top-level package for corvix."""

from importlib.metadata import PackageNotFoundError, version

__author__ = """ Rene Fritze"""
__email__ = " coding@fritze.me"

try:
    __version__ = version("corvix")
except PackageNotFoundError:
    __version__ = "unknown"
