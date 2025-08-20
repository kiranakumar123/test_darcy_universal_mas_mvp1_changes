"""
Modern orchestrator using dependency injection and async context management.
Single responsibility: coordinate logging components.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from .langsmith_tracer import LangSmithTracer
from .protocols import (
    LogEvent,
    LoggerProtocol,
    LogLevel,
    PrivacyFilterProtocol,
    TracerProtocol,
)
from .structured_logger import StructuredLogger


class ModernUniversalFrameworkLogger:
    """
    Modern orchestrator using dependency injection.
    Zero business logic - pure composition.
    """

    def __init__(
        self,
        component_name: str,
        logger: LoggerProtocol | None = None,
        tracers: list[TracerProtocol] | None = None,
        privacy_filter: PrivacyFilterProtocol | None = None,
    ):
        self.component_name = component_name

        # Modern dependency injection with defaults
        self._tracers = tracers or [LangSmithTracer("universal-framework")]
        self._privacy_filter = privacy_filter
        self._logger = logger or StructuredLogger(self._tracers, self._privacy_filter)

        # Add privacy logger for backward compatibility
        try:
            from ..compliance import PrivacySafeLogger

            self.privacy_logger = PrivacySafeLogger()
        except ImportError:
            # Create a mock privacy logger if not available
            class MockPrivacyLogger:
                class MockPIIDetector:
                    def hash_session_id(self, session_id: str) -> str:
                        import hashlib

                        return hashlib.sha256(session_id.encode()).hexdigest()[:16]

                def __init__(self):
                    self.pii_detector = self.MockPIIDetector()

            self.privacy_logger = MockPrivacyLogger()

    @asynccontextmanager
    async def logging_session(self):
        """Async context manager for resource cleanup."""
        try:
            yield self
        finally:
            await self._logger.flush()

    async def log_agent_execution(
        self,
        agent_name: str,
        session_id: str,
        execution_context: dict[str, Any],
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Modern async logging with proper error handling."""
        event = LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.INFO if success else LogLevel.ERROR,
            component=self.component_name,
            message=f"Agent {agent_name} execution {'succeeded' if success else 'failed'}",
            session_id=session_id,
            metadata={
                "agent_name": agent_name,
                "success": success,
                "error": error,
                "execution_context": execution_context,
            },
        )

        await self._logger.emit(event)

    async def log_workflow_transition(
        self,
        from_phase: str,
        to_phase: str,
        session_id: str,
        transition_context: dict[str, Any],
    ) -> None:
        """Modern workflow logging."""
        event = LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            component=self.component_name,
            message=f"Workflow transition: {from_phase} -> {to_phase}",
            session_id=session_id,
            metadata={
                "from_phase": from_phase,
                "to_phase": to_phase,
                "transition_context": transition_context,
            },
        )

        await self._logger.emit(event)

    # Legacy compatibility methods (async wrappers)
    def info(self, message: str, **kwargs) -> None:
        """Legacy compatibility - sync wrapper with fallback logging."""
        # Avoid async task creation in sync contexts to prevent destruction warnings
        # Use synchronous structured logging for production stability
        try:
            session_id = kwargs.pop("session_id", None)

            # Create structured log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "component": self.component_name,
                "message": message,
                "session_id": session_id,
                **kwargs,
            }

            # Output as JSON for structured logging compatibility
            import json

            print(json.dumps(log_entry))

        except Exception:
            # Ultimate fallback
            print(f"[INFO] {self.component_name}: {message}")

    async def _async_info(self, message: str, **kwargs) -> None:
        """Internal async implementation."""
        session_id = kwargs.pop("session_id", None)
        event = LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            component=self.component_name,
            message=message,
            session_id=session_id,
            metadata=kwargs,
        )
        await self._logger.emit(event)

    def error(self, message: str, **kwargs) -> None:
        """Legacy compatibility - sync wrapper with fallback logging."""
        # Avoid async task creation in sync contexts to prevent destruction warnings
        # Use synchronous structured logging for production stability
        try:
            session_id = kwargs.pop("session_id", None)

            # Create structured log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "component": self.component_name,
                "message": message,
                "session_id": session_id,
                **kwargs,
            }

            # Output as JSON for structured logging compatibility
            import json

            print(json.dumps(log_entry))

        except Exception:
            # Ultimate fallback
            print(f"[ERROR] {self.component_name}: {message}")

    async def _async_error(self, message: str, **kwargs) -> None:
        """Internal async implementation."""
        session_id = kwargs.pop("session_id", None)
        event = LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            component=self.component_name,
            message=message,
            session_id=session_id,
            metadata=kwargs,
        )
        await self._logger.emit(event)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message (sync wrapper)."""
        # Safely extract session_id from kwargs to avoid duplicate-key issues
        # and to prevent callers passing non-standard mapping objects from
        # causing KeyError during unpacking. Use pop with default so kwargs
        # no longer contains session_id when forwarded.
        session_id = kwargs.pop("session_id", "default")

        # Run async version in current event loop or create new one
        try:
            asyncio.get_running_loop()
            asyncio.create_task(
                self._async_warning(message, session_id=session_id, **kwargs)
            )
        except RuntimeError:
            # No event loop running, create one
            asyncio.run(self._async_warning(message, session_id=session_id, **kwargs))

    async def _async_warning(self, message: str, session_id: str = "default", **kwargs) -> None:
        """Log warning message (async).

        Accepts session_id explicitly (safer for callers that forward kwargs),
        and stores remaining kwargs in metadata.
        """
        event = LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.WARNING,
            component=self.component_name,
            message=message,
            session_id=session_id,
            metadata=kwargs,
        )
        await self._logger.emit(event)

    async def log_compliance_event(
        self,
        event_type: str,
        session_id: str,
        compliance_data: dict[str, Any],
        **kwargs,
    ) -> None:
        """Log compliance-related events."""

        event = LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            component=self.component_name,
            message=f"Compliance event: {event_type}",
            session_id=session_id,
            metadata={
                "event_type": event_type,
                "compliance_data": compliance_data,
                **kwargs,
            },
        )
        await self._logger.emit(event)

    async def log_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "ms",
        session_id: str = "default",
        **kwargs,
    ) -> None:
        """Log performance metrics."""

        event = LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            component=self.component_name,
            message=f"Performance metric: {metric_name}",
            session_id=session_id,
            metadata={
                "metric_name": metric_name,
                "value": value,
                "unit": unit,
                "metric_type": "performance",
                **kwargs,
            },
        )
        await self._logger.emit(event)

    async def log_template_operation(
        self, operation: str, template_id: str, session_id: str, **kwargs
    ) -> None:
        """Log template-related operations."""

        event = LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            component=self.component_name,
            message=f"Template operation: {operation}",
            session_id=session_id,
            metadata={
                "operation": operation,
                "template_id": template_id,
                "operation_type": "template",
                **kwargs,
            },
        )
        await self._logger.emit(event)

    async def log_email_generation(
        self, email_type: str, recipient_count: int, session_id: str, **kwargs
    ) -> None:
        """Log email generation events."""

        event = LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            component=self.component_name,
            message=f"Email generation: {email_type}",
            session_id=session_id,
            metadata={
                "email_type": email_type,
                "recipient_count": recipient_count,
                "operation_type": "email_generation",
                **kwargs,
            },
        )
        await self._logger.emit(event)

    async def log_variable_generation(
        self, variable_type: str, variable_count: int, session_id: str, **kwargs
    ) -> None:
        """Log variable generation events."""

        event = LogEvent(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            component=self.component_name,
            message=f"Variable generation: {variable_type}",
            session_id=session_id,
            metadata={
                "variable_type": variable_type,
                "variable_count": variable_count,
                "operation_type": "variable_generation",
                **kwargs,
            },
        )
        await self._logger.emit(event)

    # Legacy compatibility aliases (sync versions)
    def log_info(self, message: str, **kwargs) -> None:
        """Legacy compatibility for log_info()."""
        self.info(message, **kwargs)

    def log_error(self, message: str, **kwargs) -> None:
        """Legacy compatibility for log_error()."""
        self.error(message, **kwargs)

    def log_warning(self, message: str, **kwargs) -> None:
        """Legacy compatibility for log_warning()."""
        self.warning(message, **kwargs)

    # Setup methods for legacy compatibility
    def _setup_structured_logging(self) -> None:
        """Legacy compatibility - setup already handled in __init__."""
        pass

    def _setup_langsmith_integration(self, project: str = None) -> None:
        """Legacy compatibility - LangSmith setup already handled in __init__."""
        pass

    def _setup_otlp_integration(self) -> None:
        """Legacy compatibility - OTLP setup handled via tracers."""
        pass
