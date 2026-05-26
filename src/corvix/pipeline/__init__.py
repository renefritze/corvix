"""Shared pipeline primitives: request context, provider protocols, and the unified engine."""

from corvix.pipeline.base import JsonFetchClient, RequestContext
from corvix.pipeline.engine import PipelineEngine, PipelineRunResult, _set_nested_namespace
from corvix.pipeline.provider import ContextProvider, FieldProvider, PipelineContext

__all__ = [
    "ContextProvider",
    "FieldProvider",
    "JsonFetchClient",
    "PipelineContext",
    "PipelineEngine",
    "PipelineRunResult",
    "RequestContext",
    "_set_nested_namespace",
]
