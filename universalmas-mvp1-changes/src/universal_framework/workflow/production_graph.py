"""Enterprise StateGraph implementation using LangGraph."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from langgraph.graph import END, START, StateGraph

from universal_framework.compliance import (
    EnterpriseAuditManager,
    FailClosedStateValidator,
    PrivacySafeLogger,
)
from universal_framework.config.feature_flags import feature_flags
from universal_framework.contracts.state import UniversalWorkflowState
from universal_framework.observability import UniversalFrameworkLogger
from universal_framework.observability.simple_metrics import measure_agent_execution
from universal_framework.workflow.error_recovery import AgentCircuitBreaker, AgentStatus

logger = UniversalFrameworkLogger("production_graph")

try:  # Optional Redis checkpointing
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.checkpoint.redis import RedisSaver as _RedisSaver

    REDIS_AVAILABLE = True
    logger.info("redis_checkpointing_enabled")
except ImportError as e:  # More specific exception handling
    _RedisSaver = None
    try:
        from langgraph.checkpoint.memory import MemorySaver

        REDIS_AVAILABLE = False
        logger.info("redis_unavailable_using_memory_fallback", error=str(e))
    except ImportError:
        MemorySaver = None
        REDIS_AVAILABLE = False
        logger.warning("no_checkpointing_available", error=str(e))


@dataclass
class EnterpriseGraphConfig:
    """Configuration for EnterpriseStateGraph."""

    enable_compliance: bool = True
    enable_tracing: bool = True
    enable_monitoring: bool = True
    use_redis_checkpoint: bool = False
    redis_url: str | None = None
    node_timeout: float = 10.0
    parallelism: int = 1


class RedisOptimizedCheckpointer:
    """Redis-backed checkpointer with graceful fallback."""

    def __init__(self, conn_string: str) -> None:
        if not _RedisSaver:
            raise RuntimeError("RedisSaver unavailable")
        self._saver = _RedisSaver.from_conn_string(conn_string)

    @classmethod
    def from_conn_string(cls, conn: str) -> RedisOptimizedCheckpointer:
        return cls(conn)

    async def ainit(self) -> None:
        await self._saver.ainit()

    async def asave(self, *args: Any, **kwargs: Any) -> None:
        await self._saver.asave(*args, **kwargs)

    async def aload(self, *args: Any, **kwargs: Any) -> Any:
        return await self._saver.aload(*args, **kwargs)


class CompiledEnterpriseGraph:
    """Wrapper around compiled LangGraph graph with enterprise hooks."""

    def __init__(self, graph: Any, validator: FailClosedStateValidator | None) -> None:
        self._graph = graph
        self._validator = validator

    async def ainvoke(
        self, state: UniversalWorkflowState, **kwargs: Any
    ) -> UniversalWorkflowState:
        return await self._graph.ainvoke(state, **kwargs)

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - passthrough
        return getattr(self._graph, item)


class EnterpriseStateGraph:
    """StateGraph with enterprise features such as compliance and monitoring."""

    def __init__(
        self, state_type: type, config: EnterpriseGraphConfig | None = None
    ) -> None:
        self.state_type = state_type
        self.config = config or EnterpriseGraphConfig()
        self._graph = StateGraph(state_type)
        self._validator: FailClosedStateValidator | None = None
        if self.config.enable_compliance and feature_flags.is_enabled(
            "ENTERPRISE_FEATURES"
        ):
            logger.info("enterprise_compliance_enabled")
            privacy_logger = PrivacySafeLogger()
            from ..observability.enterprise_langsmith import EnterpriseLangSmithConfig

            langsmith_config = EnterpriseLangSmithConfig()
            audit_mgr = EnterpriseAuditManager(privacy_logger, langsmith_config)
            self._validator = FailClosedStateValidator(audit_mgr)
        elif self.config.enable_compliance:
            logger.info(
                "Enterprise compliance disabled - running in safe mode",
                event="safe_mode_active",
                enterprise_features="disabled",
            )
        self._circuit_breakers: dict[str, AgentCircuitBreaker] = {}

    # Graph API passthrough -------------------------------------------------
    def add_node(self, name: str, node: Callable[[Any], Awaitable[Any]]) -> None:
        wrapped = self._wrap_node(name, node)
        self._graph.add_node(name, wrapped)

    def add_edge(self, _from: Any, _to: Any) -> None:  # pragma: no cover - passthrough
        self._graph.add_edge(_from, _to)

    def add_conditional_edges(
        self, _from: str, router: Callable[[Any], str], edges: dict[str, Any]
    ) -> None:
        self._graph.add_conditional_edges(_from, router, edges)

    def set_entry_point(self, name: str) -> None:
        self._graph.set_entry_point(name)

    def compile(self, **kwargs: Any) -> CompiledEnterpriseGraph:
        if self.config.use_redis_checkpoint and self.config.redis_url:
            if _RedisSaver:
                kwargs.setdefault(
                    "checkpointer", _RedisSaver.from_conn_string(self.config.redis_url)
                )
            else:
                logger.warning("redis_checkpoint_unavailable")
        compiled = self._graph.compile(**kwargs)
        ce = CompiledEnterpriseGraph(compiled, self._validator)
        ce._validator = self._validator
        return ce

    # Internal helpers ------------------------------------------------------
    def _wrap_node(
        self, name: str, node_func: Callable[[Any], Awaitable[Any]]
    ) -> Callable[[UniversalWorkflowState], Awaitable[UniversalWorkflowState]]:
        circuit = AgentCircuitBreaker()
        self._circuit_breakers[name] = circuit

        async def wrapped(state: UniversalWorkflowState) -> UniversalWorkflowState:
            if circuit.state.status == AgentStatus.FAILED:
                logger.warning("circuit_open", node=name)
                return state.copy(
                    update={"error_info": {"node": name, "error": "circuit_open"}},
                    source_agent=name,
                    event="circuit_open",
                    validator=self._validator,
                )
            try:
                with measure_agent_execution(name, True):
                    if self.config.node_timeout:
                        result = await asyncio.wait_for(
                            node_func(state), timeout=self.config.node_timeout
                        )
                    else:
                        result = await node_func(state)
                circuit._record_success()
                return result
            except Exception as exc:  # pragma: no cover - error path
                logger.warning("node_execution_failed", node=name, error=str(exc))
                circuit._record_failure(exc)
                return state.copy(
                    update={"error_info": {"node": name, "error": str(exc)}},
                    source_agent=name,
                    event="node_error",
                    validator=self._validator,
                )

        if self._validator:
            wrapped._validator = self._validator  # type: ignore[attr-defined]
        return wrapped


__all__ = [
    "EnterpriseStateGraph",
    "EnterpriseGraphConfig",
    "CompiledEnterpriseGraph",
    "RedisOptimizedCheckpointer",
    "END",
    "START",
]
