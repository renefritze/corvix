"""Top-level package for corvix."""

__author__ = """ Rene Fritze"""
__email__ = " coding@fritze.me"

try:
    from . import _version

    __version__ = _version.__version__
except ImportError as e:
    print(f"version file could not be imported: {e}")
    __version__ = "unknown"
