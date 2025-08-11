"""Base node class with circuit breaker utilities."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from universal_framework.workflow.error_recovery import AgentCircuitBreaker


class BaseNode:
    """Enhanced base node with real agent circuit breaker support."""

    def __init__(self) -> None:
        self.circuit_breaker = AgentCircuitBreaker()

    async def execute_with_fallback(
        self,
        real_agent_execution: Callable[..., Any],
        simulation_fallback: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, bool]:
        """Execute with circuit breaker and fallback support."""
        return await self.circuit_breaker.execute_with_fallback(
            real_agent_execution,
            simulation_fallback,
            *args,
            **kwargs,
        )
