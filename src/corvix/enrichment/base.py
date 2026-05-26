"""Provider interfaces and shared context for enrichment.

These names are preserved for backward compatibility; the canonical definitions
live in :mod:`corvix.pipeline.provider`.
"""

from __future__ import annotations

from corvix.pipeline.base import JsonFetchClient
from corvix.pipeline.provider import ContextProvider as EnrichmentProvider
from corvix.pipeline.provider import PipelineContext as EnrichmentContext

__all__ = ["EnrichmentContext", "EnrichmentProvider", "JsonFetchClient"]
