"""
LangSmith-first tracer using modern Python patterns.
Async context manager with proper resource cleanup.
"""

from __future__ import annotations

import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace

from .protocols import LogEvent, TraceContext

# LangSmith imports with graceful fallbacks
try:
    from langchain_core.tracers.context import tracing_v2_enabled
    from langsmith import get_current_run_tree

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

    def get_current_run_tree():
        return None

    def tracing_v2_enabled():
        return False


class LangSmithTracer:
    """Modern async LangSmith tracer with resource management."""

    def __init__(self, project_name: str, sampling_rate: float = 0.1):
        self.project_name = project_name
        self.sampling_rate = sampling_rate
        self._enabled = LANGSMITH_AVAILABLE and tracing_v2_enabled()
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 3

    @asynccontextmanager
    async def tracing_session(self) -> AsyncIterator[LangSmithTracer]:
        """Async context manager for LangSmith session."""
        try:
            yield self
        finally:
            # Cleanup any pending traces
            await self._flush_pending_traces()

    async def correlate_event(self, event: LogEvent) -> LogEvent:
        """Add LangSmith trace context using modern async patterns."""
        if not self._should_trace():
            return event

        try:
            trace_context = await self._extract_trace_context()
            enhanced_metadata = {
                **event.metadata,
                "trace_context": trace_context.__dict__ if trace_context else {},
                "langsmith_project": self.project_name,
            }

            return replace(event, metadata=enhanced_metadata)

        except Exception:
            self._circuit_breaker_failures += 1
            # Return original event on failure - don't break logging
            return event

    async def _extract_trace_context(self) -> TraceContext | None:
        """Extract trace context using LangSmith APIs."""
        if not LANGSMITH_AVAILABLE:
            return None

        current_run = get_current_run_tree()

        if current_run:
            return TraceContext(
                langsmith_run_id=str(current_run.id),
                langsmith_project=self.project_name,
            )

        return TraceContext()

    def _should_trace(self) -> bool:
        """Circuit breaker + sampling logic."""
        return (
            self._enabled
            and self._circuit_breaker_failures < self._circuit_breaker_threshold
            and self._should_sample()
        )

    def _should_sample(self) -> bool:
        """Sampling decision for performance."""
        return random.random() < self.sampling_rate

    async def _flush_pending_traces(self) -> None:
        """Cleanup method for async context manager."""
        # Implementation for flushing any buffered traces
        pass

    def is_enabled(self) -> bool:
        """Protocol compliance method."""
        return (
            self._enabled
            and self._circuit_breaker_failures < self._circuit_breaker_threshold
        )
