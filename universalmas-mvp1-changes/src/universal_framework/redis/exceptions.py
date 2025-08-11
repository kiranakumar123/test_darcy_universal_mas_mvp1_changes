"""
Redis-Specific Exceptions for Universal Framework
================================================

Provides specialized exceptions for Redis operations with enterprise-grade
error context, audit trail support, and recovery guidance.
"""

from __future__ import annotations

from typing import Any

from ..contracts.exceptions import UniversalFrameworkError


class RedisConnectionError(UniversalFrameworkError):
    """Redis connection operation failed."""

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        recovery_suggestion: str | None = None,
        redis_host: str | None = None,
        redis_port: int | None = None,
    ) -> None:
        super().__init__(message, context=context)
        self.recovery_suggestion = (
            recovery_suggestion or "Check Redis server status and connection parameters"
        )
        self.redis_host = redis_host
        self.redis_port = redis_port


class SessionStorageError(UniversalFrameworkError):
    """Session storage operation failed."""

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message, context=context)
        self.session_id = session_id
        self.operation = operation


class SessionRetrievalError(SessionStorageError):
    """Session retrieval operation failed."""

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
        redis_key: str | None = None,
    ) -> None:
        super().__init__(
            message, context=context, session_id=session_id, operation="retrieve"
        )
        self.redis_key = redis_key


class SessionNotFoundError(SessionRetrievalError):
    """Session not found in Redis storage."""

    def __init__(
        self,
        session_id: str,
        *,
        context: dict[str, Any] | None = None,
        redis_key: str | None = None,
    ) -> None:
        message = f"Session not found: {session_id}"
        super().__init__(
            message, context=context, session_id=session_id, redis_key=redis_key
        )


class RedisOperationError(UniversalFrameworkError):
    """Generic Redis operation failed."""

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        operation: str | None = None,
        redis_command: str | None = None,
    ) -> None:
        super().__init__(message, context=context)
        self.operation = operation
        self.redis_command = redis_command


class KeyManagementError(UniversalFrameworkError):
    """Redis key management operation failed."""

    pass


class RedisAuthenticationError(RedisConnectionError):
    """Redis authentication failed."""

    def __init__(
        self,
        message: str = "Redis authentication failed",
        *,
        context: dict[str, Any] | None = None,
        redis_host: str | None = None,
        redis_port: int | None = None,
    ) -> None:
        super().__init__(
            message,
            context=context,
            recovery_suggestion="Verify Redis AUTH credentials and user permissions",
            redis_host=redis_host,
            redis_port=redis_port,
        )


class RedisTimeoutError(RedisConnectionError):
    """Redis operation timed out."""

    def __init__(
        self,
        message: str = "Redis operation timed out",
        *,
        context: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
        redis_host: str | None = None,
        redis_port: int | None = None,
    ) -> None:
        super().__init__(
            message,
            context=context,
            recovery_suggestion="Increase timeout or check Redis server performance",
            redis_host=redis_host,
            redis_port=redis_port,
        )
        self.timeout_seconds = timeout_seconds


class RedisMemoryError(RedisOperationError):
    """Redis out of memory error."""

    def __init__(
        self,
        message: str = "Redis out of memory",
        *,
        context: dict[str, Any] | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(
            message,
            context=context,
            operation=operation,
        )
        self.add_note(
            "Consider increasing Redis memory limit or implementing data expiration policies"
        )


class RedisDataIntegrityError(SessionStorageError):
    """Redis data integrity violation detected."""

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
        expected_data_type: str | None = None,
        actual_data_type: str | None = None,
    ) -> None:
        super().__init__(
            message, context=context, session_id=session_id, operation="integrity_check"
        )
        self.expected_data_type = expected_data_type
        self.actual_data_type = actual_data_type
