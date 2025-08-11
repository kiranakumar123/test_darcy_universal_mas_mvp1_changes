"""Enterprise session manager with Redis fallback."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any

from universal_framework.config.workflow_config import WorkflowConfig
from universal_framework.contracts.redis.validation import (
    deserialize_message,
    serialize_message,
    validate_session_data,
)
from universal_framework.observability import UniversalFrameworkLogger
from universal_framework.redis.connection import RedisConnectionAdapter
from universal_framework.redis.interfaces_stub import SessionManagerImpl as Stub
from universal_framework.redis.key_manager import RedisKeyManager


class SessionManagerImpl(Stub):
    """Concrete session manager supporting in-memory fallback."""

    def __init__(
        self,
        config: WorkflowConfig,
        connection: RedisConnectionAdapter,
        key_manager: RedisKeyManager | None = None,
    ) -> None:
        super().__init__(config, connection)
        self.key_manager = key_manager or RedisKeyManager(
            environment=os.environ.get("ENVIRONMENT", "development").lower()
        )
        self.logger = UniversalFrameworkLogger("session_manager")
        self._last_check: datetime | None = None
        self._redis_available = False

    async def is_redis_available(self) -> bool:
        """Return True if Redis connection is healthy."""
        now = datetime.utcnow()
        if self._last_check and (now - self._last_check).total_seconds() < 30:
            return self._redis_available
        self._last_check = now
        try:
            self._redis_available = await self.connection.is_healthy()
        except Exception:  # noqa: BLE001
            self._redis_available = False
        return self._redis_available

    async def create_session(
        self, session_id: str, user_id: str, use_case: str
    ) -> bool:
        ttl_seconds = int(self.config.max_session_age_hours) * 3600
        metadata = {
            "user_id": user_id,
            "use_case": use_case,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }
        if await self.is_redis_available():
            try:
                session_meta_key = self.key_manager.session_key(session_id)
                await self.connection.set_with_ttl(
                    session_meta_key, json.dumps(metadata), ttl_seconds
                )
                self.metrics["redis_operations"] += 1
                return True
            except Exception as exc:  # noqa: BLE001
                self.metrics["fallback_events"] += 1
                self.logger.warning(
                    "redis_session_create_failed",
                    session=session_id[:8],
                    error=str(exc),
                )
        if len(self.memory_storage) >= self.max_memory_sessions:
            oldest = next(iter(self.memory_storage))
            self.memory_storage.pop(oldest, None)
            self.memory_ttl.pop(oldest, None)
        self.memory_storage[session_id] = {
            "metadata": metadata,
            "data": {},
            "messages": [],
        }
        self.memory_ttl[session_id] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self.metrics["memory_operations"] += 1
        return True

    async def store_session_data(self, session_id: str, data: dict[str, Any]) -> bool:
        errors = validate_session_data(data)
        if errors:
            self.logger.warning(
                "session_data_invalid", session=session_id[:8], errors=errors
            )
            return False
        ttl_seconds = int(self.config.max_session_age_hours) * 3600
        if await self.is_redis_available():
            try:
                session_data_key = self.key_manager.state_key(session_id)
                await self.connection.set_with_ttl(
                    session_data_key, json.dumps(data), ttl_seconds
                )
                await self.update_session_activity(session_id)
                self.metrics["redis_operations"] += 1
                return True
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(
                    "redis_store_session_failed", session=session_id[:8], error=str(exc)
                )
                self.metrics["fallback_events"] += 1
        record = self.memory_storage.setdefault(
            session_id, {"metadata": {}, "data": {}, "messages": []}
        )
        record["data"] = data
        self.memory_ttl[session_id] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self.metrics["memory_operations"] += 1
        await self.update_session_activity(session_id)
        return True

    async def retrieve_session_data(self, session_id: str) -> dict[str, Any] | None:
        if await self.is_redis_available():
            try:
                session_data_key = self.key_manager.state_key(session_id)
                data = await self.connection.get(session_data_key)
                if data:
                    self.metrics["redis_operations"] += 1
                    await self.update_session_activity(session_id)
                    return json.loads(data)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(
                    "redis_retrieve_session_failed",
                    session=session_id[:8],
                    error=str(exc),
                )
                self.metrics["fallback_events"] += 1
        record = self.memory_storage.get(session_id)
        if record:
            await self.update_session_activity(session_id)
            self.metrics["memory_operations"] += 1
            return record.get("data")
        return None

    async def store_messages(self, session_id: str, messages: list[Any]) -> bool:
        serialized = [serialize_message(m) for m in messages]
        ttl_seconds = int(self.config.max_session_age_hours) * 3600
        if await self.is_redis_available():
            try:
                messages_key = self.key_manager.messages_key(session_id)
                await self.connection.set_with_ttl(
                    messages_key,
                    json.dumps(serialized),
                    ttl_seconds,
                )
                self.metrics["redis_operations"] += 1
                return True
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(
                    "redis_store_messages_failed",
                    session=session_id[:8],
                    error=str(exc),
                )
                self.metrics["fallback_events"] += 1
        record = self.memory_storage.setdefault(
            session_id, {"metadata": {}, "data": {}, "messages": []}
        )
        record["messages"] = serialized
        self.memory_ttl[session_id] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self.metrics["memory_operations"] += 1
        return True

    async def retrieve_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[Any]:
        if await self.is_redis_available():
            try:
                messages_key = self.key_manager.messages_key(session_id)
                data = await self.connection.get(messages_key)
                if data:
                    msgs = [deserialize_message(m) for m in json.loads(data)]
                    if limit:
                        msgs = msgs[-limit:]
                    self.metrics["redis_operations"] += 1
                    return msgs
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(
                    "redis_retrieve_messages_failed",
                    session=session_id[:8],
                    error=str(exc),
                )
                self.metrics["fallback_events"] += 1
        record = self.memory_storage.get(session_id)
        msgs = (
            [deserialize_message(m) for m in record.get("messages", [])]
            if record
            else []
        )
        if limit:
            msgs = msgs[-limit:]
        if record:
            self.metrics["memory_operations"] += 1
        return msgs

    async def append_message(self, session_id: str, message: Any) -> bool:
        msgs = await self.retrieve_messages(session_id)
        msgs.append(message)
        return await self.store_messages(session_id, msgs)

    async def get_message_count(self, session_id: str) -> int:
        msgs = await self.retrieve_messages(session_id)
        return len(msgs)

    async def update_session_activity(self, session_id: str) -> bool:
        now_iso = datetime.utcnow().isoformat()
        if await self.is_redis_available():
            try:
                meta_key = self.key_manager.session_key(session_id)
                data = await self.connection.get(meta_key)
                if data:
                    meta = json.loads(data)
                    meta["last_activity"] = now_iso
                    ttl_seconds = int(self.config.max_session_age_hours) * 3600
                    await self.connection.set_with_ttl(
                        meta_key, json.dumps(meta), ttl_seconds
                    )
                    self.metrics["redis_operations"] += 1
                    return True
            except Exception:
                self.metrics["fallback_events"] += 1
        record = self.memory_storage.get(session_id)
        if record:
            record.setdefault("metadata", {})["last_activity"] = now_iso
            self.metrics["memory_operations"] += 1
            return True
        return False

    async def extend_session_ttl(self, session_id: str, hours: int = 24) -> bool:
        if hours <= 0 or hours > 8760:
            return False
        ttl_seconds = hours * 3600
        if await self.is_redis_available():
            try:
                for prefix in ["session_meta", "session_data", "session_messages"]:
                    await self.connection.execute_command(
                        "EXPIRE", f"{prefix}:{session_id}", ttl_seconds
                    )
                self.metrics["redis_operations"] += 1
                return True
            except Exception:
                self.metrics["fallback_events"] += 1
        if session_id in self.memory_ttl:
            self.memory_ttl[session_id] = datetime.utcnow() + timedelta(
                seconds=ttl_seconds
            )
            self.metrics["memory_operations"] += 1
            return True
        return False

    async def cleanup_expired_sessions(self) -> int:
        now = datetime.utcnow()
        expired = [sid for sid, ts in self.memory_ttl.items() if ts < now]
        for sid in expired:
            self.memory_storage.pop(sid, None)
            self.memory_ttl.pop(sid, None)
        if expired:
            self.metrics["memory_operations"] += len(expired)
        return len(expired)

    async def get_session_stats(self) -> dict[str, Any]:
        redis_sessions = 0
        if await self.is_redis_available():
            try:
                session_pattern = self.key_manager.session_pattern()
                keys = await self.connection.scan_keys(session_pattern, 1000)
                redis_sessions = len(keys)
            except Exception:
                self.metrics["fallback_events"] += 1
        return {
            "total_sessions": redis_sessions + len(self.memory_storage),
            "redis_sessions": redis_sessions,
            "memory_sessions": len(self.memory_storage),
            "redis_connected": await self.is_redis_available(),
            **self.metrics,
        }

    async def get_active_sessions(self, user_id: str | None = None) -> list[str]:
        sessions: list[str] = []
        if await self.is_redis_available():
            try:
                session_pattern = self.key_manager.session_pattern()
                keys = await self.connection.scan_keys(session_pattern, 1000)
                for key in keys:
                    sid = self.key_manager.extract_session_id_from_key(key)
                    if sid and user_id:
                        data = await self.connection.get(key)
                        if data and json.loads(data).get("user_id") == user_id:
                            sessions.append(sid)
                    elif sid:
                        sessions.append(sid)
            except Exception:
                self.metrics["fallback_events"] += 1
        if user_id:
            sessions.extend(
                [
                    sid
                    for sid, rec in self.memory_storage.items()
                    if rec.get("metadata", {}).get("user_id") == user_id
                ]
            )
        else:
            sessions.extend(self.memory_storage.keys())
        return sessions[:1000]

    async def get_fallback_stats(self) -> dict[str, Any]:
        return {
            **self.metrics,
            "memory_sessions": len(self.memory_storage),
            "last_fallback": (
                self._last_check.isoformat()
                if self.metrics.get("fallback_events")
                else None
            ),
        }
