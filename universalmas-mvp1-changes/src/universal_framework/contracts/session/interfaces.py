from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class DataClassification(Enum):
    """Data classification levels for session storage."""

    PUBLIC = "public"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    HIGHLY_SENSITIVE = "highly_sensitive"


class SessionManagerInterface(ABC):
    """Contract interface for session management operations."""

    @abstractmethod
    async def store_session(
        self,
        session_id: str,
        data: dict[str, Any],
        classification: DataClassification = DataClassification.CONFIDENTIAL,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store session data with classification."""

    @abstractmethod
    async def retrieve_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session data."""

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""

    @abstractmethod
    async def list_sessions(self, user_id: str | None = None) -> list[str]:
        """List active session IDs."""


class AuditTrailInterface(ABC):
    """Contract interface for audit logging."""

    @abstractmethod
    async def log_operation(
        self, operation: str, session_id: str, metadata: dict[str, Any]
    ) -> str:
        """Log an operation and return audit ID."""

    @abstractmethod
    async def verify_audit_integrity(self, audit_id: str) -> bool:
        """Verify audit integrity for stored entry."""
