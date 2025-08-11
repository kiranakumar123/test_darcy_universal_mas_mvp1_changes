"""Real agent error recovery and circuit breaker patterns."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class AgentStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class CircuitBreakerState:
    status: AgentStatus
    failure_count: int
    last_failure: datetime | None
    last_success: datetime | None


class AgentCircuitBreaker:
    """Circuit breaker for real agent execution with intelligent fallback."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: timedelta = timedelta(minutes=5),
        execution_timeout: float = 5.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.execution_timeout = execution_timeout
        self.state = CircuitBreakerState(
            status=AgentStatus.HEALTHY,
            failure_count=0,
            last_failure=None,
            last_success=None,
        )

    async def execute_with_fallback(
        self,
        real_agent_func: Callable[..., Any],
        fallback_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, bool]:
        """Execute real agent with circuit breaker and fallback."""

        if self._should_skip_real_agent():
            return await fallback_func(*args, **kwargs), False

        try:
            result = await asyncio.wait_for(
                real_agent_func(*args, **kwargs),
                timeout=self.execution_timeout,
            )
            self._record_success()
            return result, True
        except Exception as e:  # noqa: BLE001
            self._record_failure(e)
            return await fallback_func(*args, **kwargs), False

    def _should_skip_real_agent(self) -> bool:
        if self.state.status == AgentStatus.HEALTHY:
            return False
        if self.state.status == AgentStatus.FAILED:
            if (
                self.state.last_failure
                and datetime.now() - self.state.last_failure > self.recovery_timeout
            ):
                self.state.status = AgentStatus.DEGRADED
                self.state.failure_count = 0
                return False
            return True
        return False

    def _record_success(self) -> None:
        self.state.last_success = datetime.now()
        self.state.failure_count = 0
        if self.state.status != AgentStatus.HEALTHY:
            self.state.status = AgentStatus.HEALTHY

    def _record_failure(self, error: Exception) -> None:
        self.state.last_failure = datetime.now()
        self.state.failure_count += 1
        if self.state.failure_count >= self.failure_threshold:
            self.state.status = AgentStatus.FAILED
        elif self.state.status == AgentStatus.HEALTHY:
            self.state.status = AgentStatus.DEGRADED
