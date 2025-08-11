"""
Structured logger using modern dependency injection patterns.
Single responsibility: emit structured JSON logs.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from .protocols import LogEvent, PrivacyFilterProtocol, TracerProtocol


class StructuredLogger:
    """Modern structured logger with protocol-based composition."""

    def __init__(
        self,
        tracers: list[TracerProtocol],
        privacy_filter: PrivacyFilterProtocol | None = None,
    ):
        self._tracers = tracers
        self._privacy_filter = privacy_filter
        self._structlog: Any = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization to prevent circular import issues."""
        if not self._initialized:
            try:
                # Use safe configuration that won't cause recursion
                structlog.configure(
                    processors=[structlog.processors.JSONRenderer()],
                    wrapper_class=structlog.make_filtering_bound_logger(
                        30
                    ),  # WARNING level
                    logger_factory=structlog.PrintLoggerFactory(),
                    cache_logger_on_first_use=True,
                )
                self._structlog = structlog.get_logger()
                self._initialized = True
            except Exception:
                # Fallback to basic logging if structlog fails
                import logging

                self._structlog = logging.getLogger("universal_framework")
                self._initialized = True

    async def emit(self, event: LogEvent) -> None:
        """Emit log event with trace correlation and privacy protection."""
        self._ensure_initialized()

        # Step 1: Apply privacy filtering
        safe_event = self._apply_privacy_filter(event)

        # Step 2: Correlate with all enabled tracers
        correlated_event = await self._correlate_with_tracers(safe_event)

        # Step 3: Emit to structlog
        await self._emit_to_structlog(correlated_event)

    def _apply_privacy_filter(self, event: LogEvent) -> LogEvent:
        """Apply privacy filtering if configured."""
        if self._privacy_filter:
            return self._privacy_filter.sanitize(event)
        return event

    async def _correlate_with_tracers(self, event: LogEvent) -> LogEvent:
        """Correlate with all enabled tracers using modern async patterns."""
        correlated_event = event

        # Use asyncio.gather for concurrent trace correlation
        correlation_tasks = [
            tracer.correlate_event(correlated_event)
            for tracer in self._tracers
            if tracer.is_enabled()
        ]

        if correlation_tasks:
            # Take the last correlation result (accumulated metadata)
            correlation_results = await asyncio.gather(
                *correlation_tasks, return_exceptions=True
            )

            # Use the last successful correlation
            for result in reversed(correlation_results):
                if not isinstance(result, Exception):
                    correlated_event = result
                    break

        return correlated_event

    async def _emit_to_structlog(self, event: LogEvent) -> None:
        """Emit to structlog with proper async handling."""
        try:
            if hasattr(self._structlog, event.level.value):
                log_method = getattr(self._structlog, event.level.value)
            else:
                log_method = self._structlog.info

            # Convert to structlog format
            log_data = {
                "timestamp": event.timestamp.isoformat(),
                "component": event.component,
                "session_id": event.session_id,
                **event.metadata,
            }

            log_method(event.message, **log_data)
        except Exception:
            # Fallback to basic print if all else fails
            print(f"[{event.level.value.upper()}] {event.component}: {event.message}")

    async def flush(self) -> None:
        """Protocol compliance: flush any buffers."""
        # Flush tracers that support it
        flush_tasks = []
        for tracer in self._tracers:
            if hasattr(tracer, "flush") and tracer.is_enabled():
                flush_tasks.append(tracer.flush())

        if flush_tasks:
            await asyncio.gather(*flush_tasks, return_exceptions=True)
