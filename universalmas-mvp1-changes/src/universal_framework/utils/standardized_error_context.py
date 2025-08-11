"""
Standardized Error Context for Universal Framework

This module provides standardized error context formatting to ensure consistent
error handling across all components, addressing the critical production issue
of inconsistent error formats causing KeyError incidents.

Unified Error Schema:
{
    "error_type": "TypeError",
    "error_message": "object str can't be used in 'await' expression",
    "error_code": "ASYNC_PATTERN_ERROR",
    "component": "intent_analyzer_chain",
    "retry_attempt": 1,
    "trace_id": "...",     // From OpenTelemetry trace context
    "span_id": "...",      // From OpenTelemetry trace context
    "timestamp": "2025-07-29T17:45:00.000Z"
}
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any


# Error code taxonomy for common framework errors
class StandardErrorCodes(Enum):
    """Standard error codes for consistent error identification"""

    # Async Pattern Errors
    ASYNC_PATTERN_ERROR = "ASYNC_PATTERN_ERROR"
    AWAIT_NON_AWAITABLE = "AWAIT_NON_AWAITABLE"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"

    # Intent Classification Errors
    INTENT_CLASSIFICATION_FAILED = "INTENT_CLASSIFICATION_FAILED"
    INVALID_INTENT_CATEGORY = "INVALID_INTENT_CATEGORY"
    CONVERSATION_HISTORY_ERROR = "CONVERSATION_HISTORY_ERROR"

    # LLM Provider Errors
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"

    # Validation Errors
    INPUT_VALIDATION_ERROR = "INPUT_VALIDATION_ERROR"
    STATE_VALIDATION_ERROR = "STATE_VALIDATION_ERROR"
    SCHEMA_VALIDATION_ERROR = "SCHEMA_VALIDATION_ERROR"

    # System Errors
    SYSTEM_ERROR = "SYSTEM_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"

    # Generic
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    GENERAL_ERROR = "GENERAL_ERROR"


class StandardizedErrorContext:
    """
    Utility class for creating standardized error contexts

    Ensures all error handling across the framework uses consistent format
    and includes trace context when available.
    """

    @staticmethod
    def create_error_context(
        error: Exception,
        component: str,
        error_code: StandardErrorCodes | str | None = None,
        retry_attempt: int = 0,
        additional_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create standardized error context from exception

        Args:
            error: The exception that occurred
            component: Component name where error occurred
            error_code: Standardized error code (auto-detected if None)
            retry_attempt: Current retry attempt number
            additional_context: Additional context to include

        Returns:
            Dict containing standardized error context
        """

        # Auto-detect error code if not provided
        if error_code is None:
            error_code = StandardizedErrorContext._detect_error_code(error)

        # Handle enum or string error codes
        if isinstance(error_code, StandardErrorCodes):
            error_code = error_code.value

        # Base error context
        error_context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_code": error_code,
            "component": component,
            "retry_attempt": retry_attempt,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        # Add trace context if available
        trace_context = StandardizedErrorContext._get_trace_context()
        if trace_context:
            error_context.update(trace_context)

        # Add additional context
        if additional_context:
            error_context.update(additional_context)

        return error_context

    @staticmethod
    def create_error_context_dict(
        error_type: str,
        error_message: str,
        component: str,
        error_code: StandardErrorCodes | str | None = None,
        retry_attempt: int = 0,
        additional_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create standardized error context from individual parameters

        Args:
            error_type: Type of error (e.g., "TypeError")
            error_message: Error message
            component: Component name where error occurred
            error_code: Standardized error code
            retry_attempt: Current retry attempt number
            additional_context: Additional context to include

        Returns:
            Dict containing standardized error context
        """

        # Default error code if not provided
        if error_code is None:
            error_code = StandardErrorCodes.GENERAL_ERROR

        # Handle enum or string error codes
        if isinstance(error_code, StandardErrorCodes):
            error_code = error_code.value

        # Base error context
        error_context = {
            "error_type": error_type,
            "error_message": error_message,
            "error_code": error_code,
            "component": component,
            "retry_attempt": retry_attempt,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        # Add trace context if available
        trace_context = StandardizedErrorContext._get_trace_context()
        if trace_context:
            error_context.update(trace_context)

        # Add additional context
        if additional_context:
            error_context.update(additional_context)

        return error_context

    @staticmethod
    def _detect_error_code(error: Exception) -> str:
        """Auto-detect error code based on exception type and message"""

        error_message = str(error).lower()
        error_type = type(error).__name__

        # Async pattern errors
        if "object str can't be used in 'await' expression" in error_message:
            return StandardErrorCodes.AWAIT_NON_AWAITABLE.value
        elif "await" in error_message and (
            "non-awaitable" in error_message or "coroutine" in error_message
        ):
            return StandardErrorCodes.ASYNC_PATTERN_ERROR.value
        elif error_type == "TimeoutError" or "timeout" in error_message:
            return StandardErrorCodes.TIMEOUT_ERROR.value

        # Intent classification errors
        elif "intent" in error_message and "classification" in error_message:
            return StandardErrorCodes.INTENT_CLASSIFICATION_FAILED.value
        elif "conversation" in error_message and "history" in error_message:
            return StandardErrorCodes.CONVERSATION_HISTORY_ERROR.value

        # LLM errors
        elif (
            "llm" in error_message
            or "openai" in error_message
            or "provider" in error_message
        ):
            return StandardErrorCodes.LLM_PROVIDER_ERROR.value
        elif "rate limit" in error_message:
            return StandardErrorCodes.LLM_RATE_LIMIT.value

        # Validation errors
        elif "validation" in error_message or error_type == "ValidationError":
            return StandardErrorCodes.INPUT_VALIDATION_ERROR.value
        elif error_type in ["ValueError", "TypeError"] and "input" in error_message:
            return StandardErrorCodes.INPUT_VALIDATION_ERROR.value

        # Generic errors
        elif error_type == "SystemError":
            return StandardErrorCodes.SYSTEM_ERROR.value
        else:
            return StandardErrorCodes.UNKNOWN_ERROR.value

    @staticmethod
    def _get_trace_context() -> dict[str, Any] | None:
        """Get current OpenTelemetry trace context if available"""

        try:
            # Try to get OpenTelemetry trace context
            from opentelemetry import trace

            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                span_context = current_span.get_span_context()
                return {
                    "trace_id": f"{span_context.trace_id:032x}",
                    "span_id": f"{span_context.span_id:016x}",
                    "trace_flags": span_context.trace_flags,
                }
        except ImportError:
            pass
        except Exception:
            pass

        try:
            # Try to get LangSmith run context
            from langsmith import get_current_run_tree

            run_tree = get_current_run_tree()
            if run_tree:
                return {"langsmith_run_id": str(run_tree.id) if run_tree.id else None}
        except ImportError:
            pass
        except Exception:
            pass

        return None


# Convenience functions for common error patterns
def create_async_error_context(
    error: Exception, component: str, retry_attempt: int = 0
) -> dict[str, Any]:
    """Create error context for async pattern errors"""
    return StandardizedErrorContext.create_error_context(
        error=error,
        component=component,
        error_code=StandardErrorCodes.ASYNC_PATTERN_ERROR,
        retry_attempt=retry_attempt,
    )


def create_intent_classification_error_context(
    error: Exception,
    component: str,
    retry_attempt: int = 0,
    user_message: str | None = None,
) -> dict[str, Any]:
    """Create error context for intent classification errors"""
    additional_context = {}
    if user_message:
        additional_context["user_message_length"] = len(user_message)
        additional_context["user_message_preview"] = (
            user_message[:100] + "..." if len(user_message) > 100 else user_message
        )

    return StandardizedErrorContext.create_error_context(
        error=error,
        component=component,
        error_code=StandardErrorCodes.INTENT_CLASSIFICATION_FAILED,
        retry_attempt=retry_attempt,
        additional_context=additional_context,
    )


def create_timeout_error_context(
    error: Exception, component: str, timeout_duration: float, retry_attempt: int = 0
) -> dict[str, Any]:
    """Create error context for timeout errors"""
    return StandardizedErrorContext.create_error_context(
        error=error,
        component=component,
        error_code=StandardErrorCodes.TIMEOUT_ERROR,
        retry_attempt=retry_attempt,
        additional_context={"timeout_duration": timeout_duration},
    )
