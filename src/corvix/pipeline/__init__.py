"""Shared pipeline primitives: request context, provider protocols, and the unified engine.

Sub-modules
-----------
:mod:`corvix.pipeline.base`
    :class:`~corvix.pipeline.base.JsonFetchClient` protocol and
    :class:`~corvix.pipeline.base.RequestContext`.

:mod:`corvix.pipeline.provider`
    :class:`~corvix.pipeline.provider.PipelineContext`,
    :class:`~corvix.pipeline.provider.FieldProvider`, and
    :class:`~corvix.pipeline.provider.ContextProvider` protocols.

:mod:`corvix.pipeline.engine`
    :class:`~corvix.pipeline.engine.PipelineEngine` and
    :class:`~corvix.pipeline.engine.PipelineRunResult`.
"""
