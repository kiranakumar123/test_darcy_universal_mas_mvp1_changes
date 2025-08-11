"""
Universal Framework Exception Hierarchy
Enterprise-grade exception handling with contextual metadata and audit integration
"""

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any

from ..contracts.redis.exceptions import RedisOperationError


class ComplianceError(Exception):
    """General compliance error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class UniversalFrameworkError(Exception):
    """Base exception for Universal Framework with enterprise context."""

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
        agent_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.session_id = session_id
        self.agent_name = agent_name
        self.timestamp = datetime.now().isoformat()
        self.stack_trace = traceback.format_exc()
        self.add_note(f"Session: {session_id}, Agent: {agent_name}, Context: {context}")

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging and monitoring."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "stack_trace": self.stack_trace,
        }


class AgentExecutionError(UniversalFrameworkError):
    """Agent execution failures with specific agent context."""

    def __init__(
        self,
        message: str,
        agent_name: str,
        execution_phase: str = "unknown",
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        enhanced_context = context or {}
        enhanced_context.update(
            {
                "execution_phase": execution_phase,
                "agent_type": "universal_agent",
            }
        )
        super().__init__(
            message=f"Agent '{agent_name}' execution failed: {message}",
            context=enhanced_context,
            session_id=session_id,
            agent_name=agent_name,
        )
        self.execution_phase = execution_phase


class StateValidationError(UniversalFrameworkError):
    """UniversalWorkflowState validation failures."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        current_phase: str | None = None,
        expected_value: Any | None = None,
        actual_value: Any | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        enhanced_context = context or {}
        enhanced_context.update(
            {
                "field_name": field_name,
                "current_phase": current_phase,
                "expected_value": str(expected_value),
                "actual_value": str(actual_value),
                "validation_type": "state_validation",
            }
        )
        super().__init__(
            message=f"State validation failed: {message}",
            context=enhanced_context,
            session_id=session_id,
        )
        self.field_name = field_name
        self.current_phase = current_phase


class WorkflowValidationError(UniversalFrameworkError):
    """Workflow and FSM validation failures."""

    def __init__(
        self,
        message: str,
        current_phase: str | None = None,
        target_phase: str | None = None,
        workflow_type: str | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        enhanced_context = context or {}
        enhanced_context.update(
            {
                "current_phase": current_phase,
                "target_phase": target_phase,
                "workflow_type": workflow_type,
                "validation_type": "workflow_validation",
            }
        )
        super().__init__(
            message=f"Workflow validation failed: {message}",
            context=enhanced_context,
            session_id=session_id,
        )


class APIValidationError(UniversalFrameworkError):
    """API request validation failures."""

    def __init__(
        self,
        message: str,
        endpoint: str | None = None,
        parameter: str | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        enhanced_context = context or {}
        enhanced_context.update(
            {
                "endpoint": endpoint,
                "parameter": parameter,
                "validation_type": "api_validation",
            }
        )
        super().__init__(
            message=f"API validation failed: {message}",
            context=enhanced_context,
            session_id=session_id,
        )


class ConfigurationError(UniversalFrameworkError):
    """Configuration and setup failures."""

    def __init__(
        self,
        message: str,
        config_section: str | None = None,
        config_key: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        enhanced_context = context or {}
        enhanced_context.update(
            {
                "config_section": config_section,
                "config_key": config_key,
                "validation_type": "configuration_validation",
            }
        )
        super().__init__(
            message=f"Configuration error: {message}", context=enhanced_context
        )


class LLMConnectionError(UniversalFrameworkError):
    """LLM connection and communication failures."""


class StrategyValidationError(UniversalFrameworkError):
    """Strategy validation and quality failures."""


class PerformanceTimeoutError(UniversalFrameworkError):
    """Performance timeout violations."""


class TemplateStoreError(UniversalFrameworkError):
    """Template storage operation failed."""


class TemplateValidationError(UniversalFrameworkError):
    """Template content validation failed."""


class TemplateNotFoundError(TemplateStoreError):
    """Requested template was not found in the store."""


__all__ = [
    "UniversalFrameworkError",
    "AgentExecutionError",
    "StateValidationError",
    "WorkflowValidationError",
    "APIValidationError",
    "ConfigurationError",
    "LLMConnectionError",
    "StrategyValidationError",
    "PerformanceTimeoutError",
    "ComplianceError",
    "RedisOperationError",
    "TemplateStoreError",
    "TemplateValidationError",
    "TemplateNotFoundError",
]
