"""Session manager implementation without circular dependencies."""

from __future__ import annotations

from typing import Optional  # noqa: UP035

from universal_framework.config.workflow_config import WorkflowConfig
from universal_framework.contracts.session.interfaces import AuditTrailInterface
from universal_framework.contracts.state import UniversalWorkflowState
from universal_framework.redis.connection import RedisConnectionAdapter

_ = (Optional, WorkflowConfig)


class EnterpriseSessionManager:
    """Enhanced session manager with Redis and optional audit integration."""

    def __init__(
        self,
        redis_adapter: RedisConnectionAdapter | None = None,
        audit_manager: AuditTrailInterface | None = None,
    ) -> None:
        self.redis_adapter = redis_adapter
        self.in_memory_fallback: dict[str, UniversalWorkflowState] = {}
        self.audit_manager = audit_manager

    async def store_session_state(
        self, session_id: str, state: UniversalWorkflowState
    ) -> bool:
        """Store full workflow state."""
        try:
            if self.redis_adapter:
                serialized = state.model_dump_json()
                await self.redis_adapter.execute_command(
                    "SETEX",
                    f"session:{session_id}",
                    86400,
                    serialized,
                )
                if self.audit_manager:
                    await self.audit_manager.log_operation(
                        "store_session_state",
                        session_id,
                        {"backend": "redis"},
                    )
                return True
        except Exception:  # noqa: BLE001
            pass

        self.in_memory_fallback[session_id] = state
        if self.audit_manager:
            await self.audit_manager.log_operation(
                "store_session_state_fallback",
                session_id,
                {"backend": "memory"},
            )
        return False

    async def get_session_state(self, session_id: str) -> UniversalWorkflowState | None:
        """Retrieve stored workflow state."""
        try:
            if self.redis_adapter:
                data = await self.redis_adapter.execute_command(
                    "GET",
                    f"session:{session_id}",
                )
                if data:
                    state = UniversalWorkflowState.model_validate_json(data)
                    if self.audit_manager:
                        await self.audit_manager.log_operation(
                            "get_session_state",
                            session_id,
                            {"backend": "redis"},
                        )
                    return state
        except Exception:  # noqa: BLE001
            pass

        cached_state = self.in_memory_fallback.get(session_id)
        if cached_state and self.audit_manager:
            await self.audit_manager.log_operation(
                "get_session_state_fallback",
                session_id,
                {"backend": "memory"},
            )
        return cached_state

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session using existing Redis patterns."""
        try:
            if self.redis_adapter:
                result = await self.redis_adapter.execute_command(
                    "DEL", f"session:{session_id}"
                )
                if self.audit_manager:
                    await self.audit_manager.log_operation(
                        "delete_session",
                        session_id,
                        {"backend": "redis", "result": bool(result)},
                    )
                return bool(result)
        except Exception:  # noqa: BLE001
            pass

        deleted = self.in_memory_fallback.pop(session_id, None) is not None
        if self.audit_manager:
            await self.audit_manager.log_operation(
                "delete_session_fallback",
                session_id,
                {"backend": "memory", "result": deleted},
            )
        return deleted

    async def list_sessions(self, user_id: str | None = None) -> list[str]:
        """List available session IDs using existing Redis patterns."""
        try:
            if self.redis_adapter:
                keys = await self.redis_adapter.execute_command("KEYS", "session:*")
                session_ids = [k.split(":", 1)[1] for k in keys if isinstance(k, str)]
                if self.audit_manager:
                    await self.audit_manager.log_operation(
                        "list_sessions",
                        "*",
                        {"backend": "redis", "count": len(session_ids)},
                    )
                return session_ids
        except Exception:  # noqa: BLE001
            pass

        session_ids = list(self.in_memory_fallback.keys())
        if self.audit_manager:
            await self.audit_manager.log_operation(
                "list_sessions_fallback",
                "*",
                {"backend": "memory", "count": len(session_ids)},
            )
        return session_ids
