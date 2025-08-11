import json
import os
from datetime import datetime
from typing import Any

from universal_framework.observability import UniversalFrameworkLogger
from universal_framework.redis.connection import RedisConnectionAdapter
from universal_framework.redis.exceptions import (
    SessionNotFoundError,
    SessionRetrievalError,
    SessionStorageError,
)
from universal_framework.redis.key_manager import RedisKeyManager


class SessionStorage:
    """Store and validate session ownership information."""

    def __init__(
        self,
        redis_adapter: RedisConnectionAdapter | None = None,
        key_manager: RedisKeyManager | None = None,
    ) -> None:
        self.redis_adapter = redis_adapter
        self.key_manager = key_manager or RedisKeyManager(
            environment=os.environ.get("ENVIRONMENT", "development").lower()
        )
        self.logger = UniversalFrameworkLogger("session_storage")
        self.session_ttl = 24 * 60 * 60  # 24 hours
        self.memory_sessions: dict[str, str] = {}

        self.allow_graceful_degradation = self._parse_bool_env(
            "REDIS_GRACEFUL_DEGRADATION",
            "true",
        )
        self.environment = os.environ.get("ENVIRONMENT", "development").lower()
        self.logger.info(
            "session_storage_initialized",
            redis_available=self.redis_adapter is not None,
            graceful_degradation_enabled=self.allow_graceful_degradation,
            environment=self.environment,
            key_manager_configured=self.key_manager is not None,
        )

    def _parse_bool_env(self, env_var: str, default: str) -> bool:
        value = os.environ.get(env_var, default).lower()
        return value in ("true", "1", "yes", "on")

    async def create_session(
        self, session_id: str, user_id: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Store new session mapping in Redis."""
        if self.redis_adapter is None:
            return await self._handle_redis_unavailable_creation(
                session_id, user_id, metadata
            )

        try:
            session_key = self.key_manager.session_key(session_id)
            user_sessions_key = self.key_manager.user_sessions_key(user_id)

            session_data = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            await self.redis_adapter.execute_command(
                "SETEX",
                session_key,
                self.session_ttl,
                json.dumps(session_data),
            )
            await self.redis_adapter.execute_command(
                "SADD", user_sessions_key, session_id
            )
            await self.redis_adapter.execute_command(
                "EXPIRE", user_sessions_key, self.session_ttl
            )
            self.logger.info(
                "session_stored",
                session=session_id[:8],
                user=user_id,
                redis_key=session_key,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "session_creation_failed",
                session=session_id[:8],
                error=str(exc),
                redis_key=session_key,
            )
            raise SessionStorageError(
                f"Failed to create session {session_id[:8]}",
                context={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(exc),
                    "redis_key": session_key,
                },
                session_id=session_id,
                operation="create",
            ) from exc

    async def session_exists(self, session_id: str) -> bool:
        """Return True if the session exists in storage."""
        if self.redis_adapter is None:
            # For memory fallback, check if session has any stored data
            # Sessions create multiple keys like session_id.intent_context, session_id.classified_intent
            return any(
                key.startswith(f"{session_id}.") or key == session_id
                for key in self.memory_sessions.keys()
            )

        try:
            session_key = self.key_manager.session_key(session_id)
            result = await self.redis_adapter.execute_command("EXISTS", session_key)
            return bool(result)
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "session_exists_check_failed",
                session=session_id[:8],
                error=str(exc),
                redis_key=session_key,
            )
            raise SessionRetrievalError(
                f"Failed to check session existence {session_id[:8]}",
                context={
                    "session_id": session_id,
                    "error": str(exc),
                    "redis_key": session_key,
                },
                session_id=session_id,
                redis_key=session_key,
            ) from exc

    async def validate_session_ownership(self, session_id: str, user_id: str) -> bool:
        """Return True if session exists and belongs to user."""
        if self.redis_adapter is None:
            return await self._handle_redis_unavailable_validation(session_id, user_id)

        try:
            session_key = self.key_manager.session_key(session_id)
            data = await self.redis_adapter.execute_command("GET", session_key)

            if not data:
                self.logger.warning(
                    "session_not_found",
                    session=session_id[:8],
                    redis_key=session_key,
                )
                raise SessionNotFoundError(
                    session_id,
                    context={"redis_key": session_key},
                    redis_key=session_key,
                )

            session_data = json.loads(data)
            stored_user = session_data.get("user_id")
            if stored_user != user_id:
                self.logger.error(
                    "ownership_mismatch",
                    expected_user=stored_user,
                    actual_user=user_id,
                    session=session_id[:8],
                    redis_key=session_key,
                )
                return False

            # Update last accessed timestamp
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            await self.redis_adapter.execute_command(
                "SETEX",
                session_key,
                self.session_ttl,
                json.dumps(session_data),
            )
            return True
        except SessionNotFoundError:
            # Re-raise specific exceptions
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "session_validation_error",
                session=session_id[:8],
                error=str(exc),
                redis_key=session_key,
            )
            raise SessionRetrievalError(
                f"Failed to validate session ownership {session_id[:8]}",
                context={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(exc),
                    "redis_key": session_key,
                },
                session_id=session_id,
                redis_key=session_key,
            ) from exc

    async def _validate_memory_session(self, session_id: str, user_id: str) -> bool:
        """Validate session ownership using in-memory store."""
        stored_data = self.memory_sessions.get(session_id)
        if not stored_data:
            return False

        try:
            # Handle both old format (direct user_id) and new format (JSON session data)
            if isinstance(stored_data, str) and stored_data.startswith("{"):
                session_data = json.loads(stored_data)
                stored_user = session_data.get("user_id")
            else:
                # Fallback for old format
                stored_user = stored_data

            if stored_user != user_id:
                self.logger.warning(
                    "memory_session_mismatch",
                    session=session_id[:8],
                    expected_user=stored_user,
                    actual_user=user_id,
                )
                return False
            return True
        except (json.JSONDecodeError, TypeError) as exc:
            self.logger.error(
                "memory_session_validation_error",
                session=session_id[:8],
                error=str(exc),
                stored_data_type=type(stored_data).__name__,
            )
            return False

    async def _handle_redis_unavailable_validation(
        self, session_id: str, user_id: str
    ) -> bool:
        """Handle session validation when Redis is unavailable."""
        self.logger.error(
            "redis_unavailable",
            session=session_id[:8],
            user_id=user_id,
            environment=self.environment,
            graceful_degradation_enabled=self.allow_graceful_degradation,
        )

        match (self.allow_graceful_degradation, self.environment):
            case (True, env) if env in ("development", "testing", "dev", "test"):
                self.logger.warning(
                    "session_validation_graceful_degradation",
                    session=session_id[:8],
                    user_id=user_id,
                    environment=self.environment,
                    reason="redis_unavailable_dev_environment",
                    security_note="graceful_degradation_active",
                )
                return True
            case (True, env) if env in ("staging", "uat"):
                self.logger.warning(
                    "session_validation_graceful_degradation",
                    session=session_id[:8],
                    user_id=user_id,
                    environment=self.environment,
                    reason="redis_unavailable_staging_environment",
                    security_note="graceful_degradation_active",
                )
                return True
            case (True, "production"):
                self.logger.critical(
                    "redis_unavailable_production_graceful_degradation_denied",
                    session=session_id[:8],
                    user_id=user_id,
                    environment=self.environment,
                    security_note="production_environment_strict_security_maintained",
                )
                return False
            case (False, _):
                self.logger.error(
                    "redis_unavailable_strict_security_mode",
                    session=session_id[:8],
                    user_id=user_id,
                    environment=self.environment,
                    security_note="graceful_degradation_disabled",
                )
                return False
            case _:
                self.logger.error(
                    "redis_unavailable_unknown_environment",
                    session=session_id[:8],
                    user_id=user_id,
                    environment=self.environment,
                    graceful_degradation_enabled=self.allow_graceful_degradation,
                    security_note="defaulting_to_strict_security",
                )
                return False

    async def _handle_redis_unavailable_creation(
        self, session_id: str, user_id: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Handle session creation when Redis is unavailable."""
        self.logger.error(
            "redis_unavailable_session_creation",
            session=session_id[:8],
            user_id=user_id,
            environment=self.environment,
            graceful_degradation_enabled=self.allow_graceful_degradation,
        )

        match (self.allow_graceful_degradation, self.environment):
            case (True, env) if env in (
                "development",
                "testing",
                "dev",
                "test",
                "staging",
                "uat",
            ):
                # Store session with full session data structure for consistency
                session_data = {
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "last_accessed": datetime.utcnow().isoformat(),
                    "metadata": metadata or {},
                }
                self.memory_sessions[session_id] = json.dumps(session_data)
                self.logger.warning(
                    "session_creation_graceful_degradation",
                    session=session_id[:8],
                    user_id=user_id,
                    environment=self.environment,
                    reason="redis_unavailable_non_production",
                    security_note="session_creation_simulated",
                )
                return True
            case _:
                self.logger.error(
                    "session_creation_failed_strict_security",
                    session=session_id[:8],
                    user_id=user_id,
                    environment=self.environment,
                    graceful_degradation_enabled=self.allow_graceful_degradation,
                    security_note="session_creation_denied",
                )
                return False

    async def get_session_data(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve full session data from Redis."""
        if self.redis_adapter is None:
            return None

        try:
            session_key = self.key_manager.session_key(session_id)
            data = await self.redis_adapter.execute_command("GET", session_key)

            if not data:
                raise SessionNotFoundError(
                    session_id,
                    context={"redis_key": session_key},
                    redis_key=session_key,
                )

            return json.loads(data)
        except SessionNotFoundError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "session_data_retrieval_failed",
                session=session_id[:8],
                error=str(exc),
                redis_key=session_key,
            )
            raise SessionRetrievalError(
                f"Failed to retrieve session data {session_id[:8]}",
                context={
                    "session_id": session_id,
                    "error": str(exc),
                    "redis_key": session_key,
                },
                session_id=session_id,
                redis_key=session_key,
            ) from exc

    async def update_session_metadata(
        self, session_id: str, metadata: dict[str, Any]
    ) -> bool:
        """Update session metadata in Redis."""
        if self.redis_adapter is None:
            return False

        try:
            session_key = self.key_manager.session_key(session_id)
            data = await self.redis_adapter.execute_command("GET", session_key)

            if not data:
                raise SessionNotFoundError(
                    session_id,
                    context={"redis_key": session_key},
                    redis_key=session_key,
                )

            session_data = json.loads(data)
            session_data["metadata"].update(metadata)
            session_data["last_accessed"] = datetime.utcnow().isoformat()

            await self.redis_adapter.execute_command(
                "SETEX",
                session_key,
                self.session_ttl,
                json.dumps(session_data),
            )

            self.logger.info(
                "session_metadata_updated",
                session=session_id[:8],
                redis_key=session_key,
            )
            return True
        except SessionNotFoundError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "session_metadata_update_failed",
                session=session_id[:8],
                error=str(exc),
                redis_key=session_key,
            )
            raise SessionStorageError(
                f"Failed to update session metadata {session_id[:8]}",
                context={
                    "session_id": session_id,
                    "metadata": metadata,
                    "error": str(exc),
                    "redis_key": session_key,
                },
                session_id=session_id,
                operation="update_metadata",
            ) from exc

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete session from Redis storage."""
        if self.redis_adapter is None:
            self.memory_sessions.pop(session_id, None)
            return True

        try:
            session_key = self.key_manager.session_key(session_id)
            user_sessions_key = self.key_manager.user_sessions_key(user_id)

            # Remove session data and user session index
            result = await self.redis_adapter.execute_command("DEL", session_key)
            await self.redis_adapter.execute_command(
                "SREM", user_sessions_key, session_id
            )

            self.logger.info(
                "session_deleted",
                session=session_id[:8],
                user=user_id,
                redis_key=session_key,
            )
            return bool(result)
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "session_deletion_failed",
                session=session_id[:8],
                error=str(exc),
                redis_key=session_key,
            )
            raise SessionStorageError(
                f"Failed to delete session {session_id[:8]}",
                context={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(exc),
                    "redis_key": session_key,
                },
                session_id=session_id,
                operation="delete",
            ) from exc

    async def get_user_sessions(self, user_id: str) -> list[str]:
        """Get all active session IDs for a user."""
        if self.redis_adapter is None:
            return [
                session_id
                for session_id, stored_user_id in self.memory_sessions.items()
                if stored_user_id == user_id
            ]

        try:
            user_sessions_key = self.key_manager.user_sessions_key(user_id)
            sessions = await self.redis_adapter.execute_command(
                "SMEMBERS", user_sessions_key
            )
            return list(sessions) if sessions else []
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "user_sessions_retrieval_failed",
                user=user_id,
                error=str(exc),
                redis_key=user_sessions_key,
            )
            raise SessionRetrievalError(
                f"Failed to retrieve user sessions for {user_id}",
                context={
                    "user_id": user_id,
                    "error": str(exc),
                    "redis_key": user_sessions_key,
                },
                redis_key=user_sessions_key,
            ) from exc

    async def store_session_data(self, session_id: str, key: str, data: Any) -> bool:
        """Store arbitrary data associated with a session."""
        if self.redis_adapter is None:
            return await self._handle_redis_unavailable_store_data(
                session_id, key, data
            )

        try:
            session_data_key = f"{self.key_manager.session_key(session_id)}.{key}"
            serialized_data = json.dumps(data) if not isinstance(data, str) else data

            result = await self.redis_adapter.execute_command(
                "SETEX",
                session_data_key,
                self.session_ttl,
                serialized_data,
            )

            self.logger.info(
                "session_data_stored",
                session_id=session_id,
                key=key,
                redis_key=session_data_key,
            )
            return bool(result)

        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "session_data_storage_failed",
                session_id=session_id,
                key=key,
                error=str(exc),
            )
            raise SessionStorageError(
                f"Failed to store session data for {session_id}",
                context={"session_id": session_id, "key": key, "error": str(exc)},
            ) from exc

    async def _handle_redis_unavailable_store_data(
        self, session_id: str, key: str, data: Any
    ) -> bool:
        """Handle session data storage when Redis is unavailable."""
        if not self.allow_graceful_degradation:
            self.logger.error(
                "session_data_storage_failed_no_redis",
                session_id=session_id,
                key=key,
                graceful_degradation=False,
            )
            raise SessionStorageError(
                "Session data storage unavailable",
                context={
                    "session_id": session_id,
                    "key": key,
                    "redis_available": False,
                },
            )

        # Store in memory with combined key
        memory_key = f"{session_id}.{key}"
        serialized_data = json.dumps(data) if not isinstance(data, str) else data
        self.memory_sessions[memory_key] = serialized_data

        self.logger.warning(
            "session_data_stored_memory_fallback",
            session_id=session_id,
            key=key,
            memory_key=memory_key,
        )
        return True
