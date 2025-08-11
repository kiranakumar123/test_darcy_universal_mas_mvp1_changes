"""
Centralized Redis Key Management for Universal Framework
======================================================

Provides collision-resistant, environment-aware, and audit-compliant
Redis key generation for all Universal Framework components.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from ..contracts.exceptions import UniversalFrameworkError


class KeyManagementError(UniversalFrameworkError):
    """Redis key management operation failed."""

    pass


class RedisKeyManager:
    """
    Centralized Redis key management for Universal Framework.

    Provides collision-resistant key generation with environment isolation,
    audit trail support, and enterprise-grade key validation.
    """

    def __init__(
        self,
        key_prefix: str = "universal_framework",
        environment: str = "prod",
        enable_key_hashing: bool = False,
    ) -> None:
        """
        Initialize Redis key manager.

        Args:
            key_prefix: Base prefix for all keys (default: "universal_framework")
            environment: Environment identifier (default: "prod")
            enable_key_hashing: Whether to hash sensitive parts of keys
        """
        self.key_prefix = key_prefix
        self.environment = environment
        self.enable_key_hashing = enable_key_hashing

        # Key pattern validation - initialize before validation
        self._key_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
        self._max_key_length = (
            250  # Redis max key length is 512MB, but keeping practical
        )

        # Validate configuration after pattern is set
        self._validate_key_safety()

    def session_key(self, session_id: str) -> str:
        """
        Generate collision-resistant session key.

        Args:
            session_id: Unique session identifier

        Returns:
            Formatted Redis key for session data

        Raises:
            KeyManagementError: If session_id is invalid
        """
        self._validate_session_id(session_id)

        if self.enable_key_hashing:
            session_hash = self._hash_sensitive_data(session_id)
            return f"{self.key_prefix}:{self.environment}:session:{session_hash}"

        return f"{self.key_prefix}:{self.environment}:session:{session_id}"

    def workflow_key(self, session_id: str, workflow_phase: str) -> str:
        """
        Generate workflow state key.

        Args:
            session_id: Unique session identifier
            workflow_phase: Current workflow phase (e.g., "discovery", "analysis")

        Returns:
            Formatted Redis key for workflow state data
        """
        self._validate_session_id(session_id)
        self._validate_component_name(workflow_phase, "workflow_phase")

        if self.enable_key_hashing:
            session_hash = self._hash_sensitive_data(session_id)
            return f"{self.key_prefix}:{self.environment}:workflow:{session_hash}:{workflow_phase}"

        return f"{self.key_prefix}:{self.environment}:workflow:{session_id}:{workflow_phase}"

    def agent_key(self, session_id: str, agent_name: str) -> str:
        """
        Generate agent execution key.

        Args:
            session_id: Unique session identifier
            agent_name: Name of the executing agent

        Returns:
            Formatted Redis key for agent execution data
        """
        self._validate_session_id(session_id)
        self._validate_component_name(agent_name, "agent_name")

        if self.enable_key_hashing:
            session_hash = self._hash_sensitive_data(session_id)
            return f"{self.key_prefix}:{self.environment}:agent:{session_hash}:{agent_name}"

        return f"{self.key_prefix}:{self.environment}:agent:{session_id}:{agent_name}"

    def audit_key(self, session_id: str, timestamp: str | None = None) -> str:
        """
        Generate audit trail key.

        Args:
            session_id: Unique session identifier
            timestamp: ISO timestamp (optional, defaults to current time)

        Returns:
            Formatted Redis key for audit trail data
        """
        self._validate_session_id(session_id)

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # Clean timestamp for key safety
        clean_timestamp = timestamp.replace(":", "_").replace(".", "_")

        if self.enable_key_hashing:
            session_hash = self._hash_sensitive_data(session_id)
            return f"{self.key_prefix}:{self.environment}:audit:{session_hash}:{clean_timestamp}"

        return (
            f"{self.key_prefix}:{self.environment}:audit:{session_id}:{clean_timestamp}"
        )

    def checkpoint_key(self, session_id: str, checkpoint_id: str) -> str:
        """
        Generate checkpoint key.

        Args:
            session_id: Unique session identifier
            checkpoint_id: Unique checkpoint identifier

        Returns:
            Formatted Redis key for checkpoint data
        """
        self._validate_session_id(session_id)
        self._validate_component_name(checkpoint_id, "checkpoint_id")

        if self.enable_key_hashing:
            session_hash = self._hash_sensitive_data(session_id)
            return f"{self.key_prefix}:{self.environment}:checkpoint:{session_hash}:{checkpoint_id}"

        return f"{self.key_prefix}:{self.environment}:checkpoint:{session_id}:{checkpoint_id}"

    def user_sessions_key(self, user_id: str) -> str:
        """
        Generate user sessions index key.

        Args:
            user_id: Unique user identifier

        Returns:
            Formatted Redis key for user session index
        """
        self._validate_component_name(user_id, "user_id")

        if self.enable_key_hashing:
            user_hash = self._hash_sensitive_data(user_id)
            return f"{self.key_prefix}:{self.environment}:user_sessions:{user_hash}"

        return f"{self.key_prefix}:{self.environment}:user_sessions:{user_id}"

    def messages_key(self, session_id: str) -> str:
        """
        Generate session messages key.

        Args:
            session_id: Unique session identifier

        Returns:
            Formatted Redis key for session messages
        """
        self._validate_session_id(session_id)

        if self.enable_key_hashing:
            session_hash = self._hash_sensitive_data(session_id)
            return f"{self.key_prefix}:{self.environment}:messages:{session_hash}"

        return f"{self.key_prefix}:{self.environment}:messages:{session_id}"

    def state_key(self, session_id: str) -> str:
        """
        Generate workflow state key.

        Args:
            session_id: Unique session identifier

        Returns:
            Formatted Redis key for workflow state
        """
        self._validate_session_id(session_id)

        if self.enable_key_hashing:
            session_hash = self._hash_sensitive_data(session_id)
            return f"{self.key_prefix}:{self.environment}:state:{session_hash}"

        return f"{self.key_prefix}:{self.environment}:state:{session_id}"

    def _validate_session_id(self, session_id: str) -> None:
        """
        Validate session ID for key safety.

        Args:
            session_id: Session identifier to validate

        Raises:
            KeyManagementError: If session_id is invalid
        """
        if not session_id:
            raise KeyManagementError(
                "Session ID cannot be empty", context={"session_id": repr(session_id)}
            )

        if len(session_id) < 8:
            raise KeyManagementError(
                f"Session ID too short (minimum 8 characters): {len(session_id)}",
                context={"session_id": session_id, "length": len(session_id)},
            )

        if ":" in session_id:
            raise KeyManagementError(
                "Session ID cannot contain ':' character (Redis key delimiter)",
                context={"session_id": session_id},
            )

        if not self._key_pattern.match(session_id):
            raise KeyManagementError(
                "Session ID contains invalid characters (only alphanumeric, _, - allowed)",
                context={"session_id": session_id},
            )

    def _validate_component_name(self, name: str, component_type: str) -> None:
        """
        Validate component name for key safety.

        Args:
            name: Component name to validate
            component_type: Type of component for error reporting

        Raises:
            KeyManagementError: If name is invalid
        """
        if not name:
            raise KeyManagementError(
                f"{component_type} cannot be empty",
                context={component_type: repr(name)},
            )

        if ":" in name:
            raise KeyManagementError(
                f"{component_type} cannot contain ':' character (Redis key delimiter)",
                context={component_type: name},
            )

        if not self._key_pattern.match(name):
            raise KeyManagementError(
                f"{component_type} contains invalid characters (only alphanumeric, _, - allowed)",
                context={component_type: name},
            )

    def _validate_key_safety(self) -> None:
        """
        Validate key configuration for collision prevention.

        Raises:
            KeyManagementError: If configuration is unsafe
        """
        if ":" in self.key_prefix:
            raise KeyManagementError(
                "Key prefix cannot contain ':' character",
                context={"key_prefix": self.key_prefix},
            )

        if ":" in self.environment:
            raise KeyManagementError(
                "Environment cannot contain ':' character",
                context={"environment": self.environment},
            )

        if not self._key_pattern.match(self.key_prefix):
            raise KeyManagementError(
                "Key prefix contains invalid characters",
                context={"key_prefix": self.key_prefix},
            )

        if not self._key_pattern.match(self.environment):
            raise KeyManagementError(
                "Environment contains invalid characters",
                context={"environment": self.environment},
            )

    def _hash_sensitive_data(self, data: str) -> str:
        """
        Hash sensitive data for privacy protection.

        Args:
            data: Sensitive data to hash

        Returns:
            SHA-256 hash of the data (first 16 characters)
        """
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def validate_key_format(self, key: str) -> bool:
        """
        Validate that a key follows the expected format.

        Args:
            key: Redis key to validate

        Returns:
            True if key follows expected format
        """
        expected_prefix = f"{self.key_prefix}:{self.environment}:"
        return key.startswith(expected_prefix) and len(key) <= self._max_key_length

    def get_key_metadata(self, key: str) -> dict[str, Any]:
        """
        Extract metadata from a properly formatted key.

        Args:
            key: Redis key to analyze

        Returns:
            Dictionary with key metadata
        """
        if not self.validate_key_format(key):
            return {"valid": False, "error": "Invalid key format"}

        parts = key.split(":")
        if len(parts) < 4:
            return {"valid": False, "error": "Insufficient key parts"}

        return {
            "valid": True,
            "prefix": parts[0],
            "environment": parts[1],
            "key_type": parts[2],
            "identifier": parts[3] if len(parts) > 3 else None,
            "component": parts[4] if len(parts) > 4 else None,
        }

    def session_pattern(self) -> str:
        """
        Get Redis key pattern for session keys.

        Returns:
            Pattern string suitable for Redis SCAN operations
        """
        return f"{self.key_prefix}:{self.environment}:session:*"

    def workflow_pattern(self) -> str:
        """
        Get Redis key pattern for workflow keys.

        Returns:
            Pattern string suitable for Redis SCAN operations
        """
        return f"{self.key_prefix}:{self.environment}:workflow:*"

    def agent_pattern(self) -> str:
        """
        Get Redis key pattern for agent keys.

        Returns:
            Pattern string suitable for Redis SCAN operations
        """
        return f"{self.key_prefix}:{self.environment}:agent:*"

    def extract_session_id_from_key(self, key: str) -> str | None:
        """
        Extract session ID from a properly formatted session key.

        Args:
            key: Redis session key

        Returns:
            Session ID if valid, None otherwise
        """
        metadata = self.get_key_metadata(key)
        if metadata["valid"] and metadata["key_type"] == "session":
            return metadata["identifier"]
        return None
