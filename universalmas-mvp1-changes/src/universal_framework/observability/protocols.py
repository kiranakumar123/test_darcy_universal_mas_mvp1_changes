"""
Modern Python protocols for logging system composition.
Uses Protocol classes for dependency injection and testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol


class LogLevel(str, Enum):
    """Modern enum for log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class LogEvent:
    """Immutable log event with LangSmith correlation."""

    timestamp: datetime
    level: LogLevel
    component: str
    message: str
    session_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


@dataclass(frozen=True, slots=True)
class TraceContext:
    """OpenTelemetry + LangSmith trace correlation."""

    trace_id: str | None = None
    span_id: str | None = None
    langsmith_run_id: str | None = None
    langsmith_project: str | None = None


class TracerProtocol(Protocol):
    """Protocol for trace correlation systems."""

    async def correlate_event(self, event: LogEvent) -> LogEvent:
        """Add trace context to log event."""
        ...

    def is_enabled(self) -> bool:
        """Check if tracer is operational."""
        ...


class LoggerProtocol(Protocol):
    """Protocol for structured logging backends."""

    async def emit(self, event: LogEvent) -> None:
        """Emit log event to backend."""
        ...

    async def flush(self) -> None:
        """Flush any buffered events."""
        ...


class PrivacyFilterProtocol(Protocol):
    """Protocol for PII protection."""

    def sanitize(self, event: LogEvent) -> LogEvent:
        """Remove PII from log event."""
        ...
