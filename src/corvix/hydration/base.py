"""Provider interfaces and shared context for hydration.

These names are preserved for backward compatibility; the canonical definitions
live in :mod:`corvix.pipeline.provider`.
"""

from __future__ import annotations

from corvix.pipeline.provider import FieldProvider as HydrationProvider
from corvix.pipeline.provider import PipelineContext as HydrationContext

__all__ = ["HydrationContext", "HydrationProvider"]
