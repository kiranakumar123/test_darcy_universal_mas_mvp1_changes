# ruff: noqa: I001,UP035,UP006
import asyncio
from typing import Any

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from universal_framework.config.workflow_config import WorkflowConfig
from universal_framework.contracts.redis.exceptions import (
    RedisConnectionError,
    RedisTimeoutError,
    RedisAuthError,
)
from universal_framework.redis.interfaces_stub import (
    RedisConnectionAdapter as RedisConnectionInterface,
    ConnectionStatus,
)


class RedisConnectionAdapter(RedisConnectionInterface):
    """Enterprise Redis connection adapter implementation."""

    def __init__(self, config: WorkflowConfig):
        if not REDIS_AVAILABLE:
            raise RedisConnectionError("redis package not available")
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self.connection_pool: Any | None = None
        self.last_error: str | None = None
        self.retry_count = 0
        self.max_retries = 3

    async def connect(self) -> bool:
        """Establish Redis connection with retry and pooling."""
        connection_url = self.config.redis_url
        if not connection_url:
            auth = (
                f":{self.config.redis_password}@" if self.config.redis_password else ""
            )
            connection_url = (
                f"redis://{auth}{self.config.redis_host}:{self.config.redis_port}/"
                f"{self.config.redis_db}"
            )
        for attempt in range(self.max_retries):
            try:
                self.connection_pool = redis.from_url(
                    connection_url,
                    decode_responses=True,
                )
                await self.connection_pool.ping()
                self.status = ConnectionStatus.CONNECTED
                self.retry_count = 0
                return True
            except redis.AuthenticationError as exc:
                self.status = ConnectionStatus.ERROR
                self.last_error = "auth_failed"
                raise RedisAuthError("Authentication failed") from exc
            except redis.TimeoutError as exc:
                self.retry_count += 1
                self.status = ConnectionStatus.TIMEOUT
                self.last_error = "timeout"
                if attempt + 1 >= self.max_retries:
                    raise RedisTimeoutError("Connection timeout") from exc
            except Exception as exc:  # noqa: BLE001
                self.retry_count += 1
                self.status = ConnectionStatus.ERROR
                self.last_error = str(exc)
                if attempt + 1 >= self.max_retries:
                    raise RedisConnectionError("Unable to connect to Redis") from exc
            await asyncio.sleep(2**attempt)
        return False

    async def disconnect(self) -> None:
        """Gracefully close Redis connection."""
        if self.connection_pool is not None:
            try:
                await self.connection_pool.close()
            except Exception:
                pass
            finally:
                self.connection_pool = None
        self.status = ConnectionStatus.DISCONNECTED
        self.last_error = None

    async def ping(self) -> bool:
        """Ping Redis server to verify responsiveness."""
        if self.connection_pool is None:
            return False
        try:
            await self.connection_pool.ping()
            self.status = ConnectionStatus.CONNECTED
            return True
        except Exception:  # noqa: BLE001
            self.status = ConnectionStatus.ERROR
            return False

    async def is_healthy(self) -> bool:
        """Return True if connection is healthy and ping time <100ms."""
        if self.status != ConnectionStatus.CONNECTED:
            return False
        start_time = asyncio.get_event_loop().time()
        ping_result = await self.ping()
        ping_time = (asyncio.get_event_loop().time() - start_time) * 1000
        return ping_result and ping_time < 100.0

    async def get_info(self) -> dict[str, Any]:
        """Return Redis server INFO data."""
        if self.connection_pool is None:
            return {}
        try:
            info: dict[str, Any] = await self.connection_pool.info()
            return {
                "version": info.get("redis_version"),
                "memory_usage": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
            }
        except Exception:  # noqa: BLE001
            return {}

    async def execute_command(self, command: str, *args, **kwargs) -> Any:
        """Execute a raw Redis command.

        Raises:
            RedisConnectionError: If not connected
            RedisTimeoutError: If operation times out
        """
        if self.connection_pool is None or self.status != ConnectionStatus.CONNECTED:
            raise RedisConnectionError("Not connected")
        timeout = int(getattr(self.config, "agent_timeout_seconds", 5))
        try:
            return await asyncio.wait_for(
                self.connection_pool.execute_command(command, *args, **kwargs),
                timeout=timeout,
            )
        except TimeoutError as exc:
            self.status = ConnectionStatus.TIMEOUT
            self.last_error = "timeout"
            raise RedisTimeoutError("Redis command timed out") from exc
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            raise RedisConnectionError("Redis command failed") from exc

    async def set_with_ttl(self, key: str, value: str, ttl_seconds: int) -> bool:
        """Set key with TTL."""
        if ttl_seconds <= 0:
            return False
        try:
            await self.execute_command("SET", key, value, "EX", ttl_seconds)
            return True
        except RedisConnectionError:
            return False

    async def get(self, key: str) -> str | None:
        """Get value for key."""
        try:
            result = await self.execute_command("GET", key)
            return result if result is not None else None
        except RedisConnectionError:
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        try:
            result = await self.execute_command("DEL", key)
            return bool(result)
        except RedisConnectionError:
            return False

    async def scan_keys(self, pattern: str, count: int = 100) -> list[str]:
        """Scan and return keys matching a pattern."""
        if count <= 0 or self.connection_pool is None:
            return []
        try:
            cursor = 0
            keys: list[str] = []
            while cursor != 0 or len(keys) == 0:
                cursor, batch = await self.connection_pool.scan(
                    cursor=cursor, match=pattern, count=min(count - len(keys), 100)
                )
                keys.extend(batch)
                if len(keys) >= count:
                    break
            return keys[:count]
        except Exception:  # noqa: BLE001
            return []
