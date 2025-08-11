"""
Enterprise Redis Key Management
===============================

Hierarchical key naming with versioning and namespace isolation.
Follows enterprise patterns for key hygiene and collision prevention.
"""

import hashlib
from enum import Enum

from .exceptions import RedisKeyError


class KeyType(Enum):
    """Redis key types for namespace organization."""

    SESSION_MESSAGES = "messages"
    SESSION_DATA = "data"
    SESSION_METADATA = "metadata"
    SESSION_CHECKPOINTS = "checkpoints"
    GLOBAL_STATS = "stats"
    USER_SESSIONS = "user_sessions"


class RedisKeyManager:
    """Centralized Redis key management with enterprise naming conventions."""

    def __init__(
        self, system_name: str = "universal_framework", environment: str = "prod"
    ):
        self.system_name = system_name
        self.environment = environment
        self.schema_version = 1

    def template_key(self, template_id: str, template_type: str) -> str:
        """Generate key for stored template."""
        return ":".join(
            [
                "global",
                self.system_name,
                self.environment,
                "template",
                template_id,
                template_type,
                f"v{self.schema_version}",
            ]
        )

    def template_pattern_by_type(self, template_type: str) -> str:
        """Pattern for templates by type."""
        return f"global:{self.system_name}:{self.environment}:template:*:{template_type}:v{self.schema_version}*"

    def build_session_key(
        self, key_type: KeyType, session_id: str, suffix: str | None = None
    ) -> str:
        """
        Build hierarchical session key.

        Format: session:<system>:<env>:<key_type>:<session_id>:v<version>[:<suffix>]
        Example: session:universal_framework:prod:messages:abc123:v1
        """
        if not session_id:
            raise RedisKeyError("Session ID cannot be empty")

        # Validate session ID format (basic check)
        if len(session_id) < 8 or len(session_id) > 64:
            raise RedisKeyError("Session ID must be 8-64 characters")

        # Build key components
        components = [
            "session",
            self.system_name,
            self.environment,
            key_type.value,
            session_id,
            f"v{self.schema_version}",
        ]

        if suffix:
            components.append(suffix)

        return ":".join(components)

    def build_user_key(self, user_id: str, suffix: str | None = None) -> str:
        """
        Build user-scoped key.

        Format: user:<system>:<env>:<user_id>:v<version>[:<suffix>]
        """
        if not user_id:
            raise RedisKeyError("User ID cannot be empty")

        # Hash user ID for privacy (optional, based on requirements)
        user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]

        components = [
            "user",
            self.system_name,
            self.environment,
            user_hash,
            f"v{self.schema_version}",
        ]

        if suffix:
            components.append(suffix)

        return ":".join(components)

    def build_global_key(self, key_type: KeyType, identifier: str) -> str:
        """
        Build global system key.

        Format: global:<system>:<env>:<key_type>:<identifier>:v<version>
        """
        components = [
            "global",
            self.system_name,
            self.environment,
            key_type.value,
            identifier,
            f"v{self.schema_version}",
        ]

        return ":".join(components)

    def parse_key(self, key: str) -> dict[str, str | None]:
        """Parse Redis key into components."""
        try:
            parts = key.split(":")
            if len(parts) < 6:
                raise RedisKeyError(f"Invalid key format: {key}")

            return {
                "scope": parts[0],
                "system": parts[1],
                "environment": parts[2],
                "key_type": parts[3],
                "identifier": parts[4],
                "version": parts[5],
                "suffix": ":".join(parts[6:]) if len(parts) > 6 else None,
            }
        except Exception as err:
            raise RedisKeyError(f"Failed to parse key {key}: {err}") from err

    def get_pattern(
        self, scope: str = "*", key_type: str = "*", identifier: str = "*"
    ) -> str:
        """Get Redis pattern for key scanning."""
        return f"{scope}:{self.system_name}:{self.environment}:{key_type}:{identifier}:v{self.schema_version}*"

    def validate_key(self, key: str) -> bool:
        """Validate key format and components."""
        try:
            parsed = self.parse_key(key)

            # Check required components
            required = [
                "scope",
                "system",
                "environment",
                "key_type",
                "identifier",
                "version",
            ]
            for component in required:
                if not parsed.get(component):
                    return False

            # Check system match
            if parsed["system"] != self.system_name:
                return False

            # Check version format
            version = parsed.get("version")
            return not (not version or not version.startswith("v"))
        except Exception:
            return False


class SessionKeyBuilder:
    """Convenience builder for session-specific keys."""

    def __init__(self, key_manager: RedisKeyManager):
        self.key_manager = key_manager

    def messages_key(self, session_id: str) -> str:
        """Get key for session messages."""
        return self.key_manager.build_session_key(KeyType.SESSION_MESSAGES, session_id)

    def data_key(self, session_id: str) -> str:
        """Get key for session data."""
        return self.key_manager.build_session_key(KeyType.SESSION_DATA, session_id)

    def metadata_key(self, session_id: str) -> str:
        """Get key for session metadata."""
        return self.key_manager.build_session_key(KeyType.SESSION_METADATA, session_id)

    def checkpoints_key(self, session_id: str) -> str:
        """Get key for session checkpoints."""
        return self.key_manager.build_session_key(
            KeyType.SESSION_CHECKPOINTS, session_id
        )

    def user_sessions_key(self, user_id: str) -> str:
        """Get key for user's active sessions."""
        return self.key_manager.build_user_key(user_id, "sessions")


# Global instances (can be configured via environment)
_default_key_manager = RedisKeyManager()
_default_session_builder = SessionKeyBuilder(_default_key_manager)


def get_session_key(key_type: KeyType, session_id: str) -> str:
    """Convenience function for session keys."""
    return _default_key_manager.build_session_key(key_type, session_id)


def get_message_key(session_id: str) -> str:
    """Convenience function for message keys."""
    return _default_session_builder.messages_key(session_id)


def configure_key_manager(system_name: str, environment: str) -> None:
    """Configure global key manager settings."""
    global _default_key_manager, _default_session_builder
    _default_key_manager = RedisKeyManager(system_name, environment)
    _default_session_builder = SessionKeyBuilder(_default_key_manager)
