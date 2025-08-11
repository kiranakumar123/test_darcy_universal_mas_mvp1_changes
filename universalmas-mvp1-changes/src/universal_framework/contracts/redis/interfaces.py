"""
Enterprise Redis Interface Contracts
====================================

Abstract interfaces following enterprise patterns from LangChain, Semantic Kernel, AutoGen.
These interfaces define the contract boundary for all Redis operations.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from langchain_core.messages import BaseMessage

# Note: WorkflowPhase imported from state contracts to maintain single source of truth.
# Current email workflow phases: BATCH_DISCOVERY, STRATEGY_ANALYSIS, STRATEGY_CONFIRMATION, etc.
from universal_framework.contracts.state import WorkflowPhase  # noqa: F401


class SessionDataInterface(ABC):
    """Interface for session data operations."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for Redis storage."""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionDataInterface":
        """Deserialize from Redis dictionary."""
        pass

    @abstractmethod
    def validate(self) -> list[str]:
        """Validate data integrity. Returns list of errors (empty if valid)."""
        pass


class MessageStoreInterface(ABC):
    """Interface for message storage operations."""

    @abstractmethod
    async def store_messages(
        self, session_id: str, messages: list[BaseMessage]
    ) -> bool:
        """Store session messages. Returns True if successful."""
        pass

    @abstractmethod
    async def retrieve_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[BaseMessage]:
        """Retrieve session messages with optional limit."""
        pass

    @abstractmethod
    async def append_message(self, session_id: str, message: BaseMessage) -> bool:
        """Append single message to session. Returns True if successful."""
        pass

    @abstractmethod
    async def get_message_count(self, session_id: str) -> int:
        """Get total message count for session."""
        pass


class RedisConnectionInterface(ABC):
    """Interface for Redis connection management."""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish Redis connection. Returns True if successful."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close Redis connection gracefully."""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check Redis connection health."""
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """Ping Redis server. Returns True if responsive."""
        pass

    @abstractmethod
    async def get_info(self) -> dict[str, Any]:
        """Get Redis server information."""
        pass


class RedisSessionManagerInterface(ABC):
    """Primary interface for Redis session management operations."""

    @abstractmethod
    async def create_session(
        self, session_id: str, user_id: str, use_case: str
    ) -> bool:
        """Create new session with metadata. Returns True if successful."""
        pass

    @abstractmethod
    async def store_session_data(
        self, session_id: str, data: SessionDataInterface
    ) -> bool:
        """Store session state data. Returns True if successful."""
        pass

    @abstractmethod
    async def retrieve_session_data(
        self, session_id: str
    ) -> SessionDataInterface | None:
        """Retrieve session state data. Returns None if not found."""
        pass

    @abstractmethod
    async def update_session_activity(self, session_id: str) -> bool:
        """Update last activity timestamp. Returns True if successful."""
        pass

    @abstractmethod
    async def extend_session_ttl(self, session_id: str, hours: int = 24) -> bool:
        """Extend session TTL. Returns True if successful."""
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions. Returns count of cleaned sessions."""
        pass

    @abstractmethod
    async def get_session_stats(self) -> dict[str, Any]:
        """Get overall session statistics."""
        pass

    @abstractmethod
    async def get_active_sessions(self, user_id: str | None = None) -> list[str]:
        """Get list of active session IDs, optionally filtered by user."""
        pass


class UseCase(Enum):
    """Enum for supported use cases."""

    OCM_COMMUNICATIONS = "ocm_communications"
    DOCUMENT_GENERATION = "document_generation"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    PROCESS_DESIGN = "process_design"


# Type aliases for clarity
SessionID = str
UserID = str
MessageID = str
RedisKey = str
TTLSeconds = int
