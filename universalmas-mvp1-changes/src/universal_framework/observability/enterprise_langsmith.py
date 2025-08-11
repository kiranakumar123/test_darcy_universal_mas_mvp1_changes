"""Enterprise LangSmith observability utilities."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from langsmith import Client

from universal_framework.compliance import (
    PIIDetector,
    PrivacySafeLogger,
    RedactionConfig,
)
from universal_framework.config.environment import get_langsmith_config
from universal_framework.config.feature_flags import feature_flags

from ..core.logging_foundation import get_safe_logger


@dataclass(slots=True, init=False)
class EnterpriseLangSmithConfig:
    """Enterprise LangSmith configuration container."""

    pii_detector: PIIDetector | None = field(default=None)
    enterprise_settings: dict[str, Any] = field(default_factory=dict)
    project_name: str = "universal-framework"
    circuit_breaker: LangSmithCircuitBreaker | None = None
    basic_config: dict[str, Any] = field(default_factory=dict)
    api_key: str | None = None
    _enterprise_client: Client | None = None

    def __init__(
        self,
        config_path: Path | str | None = None,
        pii_detector: PIIDetector | None = None,
    ) -> None:
        # Only create PII detector if feature is enabled
        if feature_flags.is_enabled("PII_REDACTION"):
            self.pii_detector = pii_detector or PIIDetector(RedactionConfig())
        else:
            self.pii_detector = None
        config = get_langsmith_config(config_path)
        self.basic_config = config
        self.enterprise_settings = config
        self.project_name = config.get("project", "universal-framework")
        self.api_key = config.get("api_key")
        self.circuit_breaker = LangSmithCircuitBreaker(self.enterprise_settings)
        self._enterprise_client = None

    def create_privacy_safe_trace_metadata(
        self, agent_name: str, session_id: str
    ) -> dict[str, Any]:
        """Create base privacy-safe metadata for LangSmith traces."""

        if self.pii_detector:
            session_hash = self.pii_detector.hash_session_id(session_id)
        else:
            # Safe mode - simple hash without PII detection
            session_hash = f"session_hash_{hash(session_id) % 100000:05d}"
        return {
            "session_hash": session_hash,
            "agent_name": agent_name,
            "project_name": self.project_name,
        }


class LangSmithCircuitBreakerError(Exception):
    """Raised when LangSmith circuit is open and calls are blocked."""


class LangSmithCircuitBreaker:
    """Circuit breaker for LangSmith operations."""

    def __init__(self, enterprise_settings: dict[str, Any]):
        self.enterprise_settings = enterprise_settings
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "CLOSED"
        self.failure_threshold = enterprise_settings.get("failure_threshold", 5)
        self.recovery_timeout = enterprise_settings.get(
            "recovery_timeout_seconds", 60.0
        )
        self._lock = asyncio.Lock()
        from .logging_contracts import LoggingFactory

        self.logger = LoggingFactory.create_observability_logger("langsmith_circuit")

    async def __aenter__(self) -> LangSmithCircuitBreaker:
        async with self._lock:
            if self.state == "OPEN":
                if (
                    self.last_failure_time
                    and (datetime.now() - self.last_failure_time).total_seconds()
                    > self.recovery_timeout
                ):
                    self.state = "HALF_OPEN"
                    self.failure_count = 0
                    self.logger.log_compliance_event(
                        event_type="circuit_state_change",
                        event_data={"state": "half_open", "recovery_attempt": True},
                    )
                else:
                    raise LangSmithCircuitBreakerError(
                        "LangSmith circuit breaker is OPEN"
                    )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        async with self._lock:
            if exc_type is None:
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.logger.log_compliance_event(
                        event_type="circuit_state_change",
                        event_data={"state": "closed"},
                    )
                self.failure_count = 0
            else:
                self.failure_count += 1
                self.last_failure_time = datetime.now()
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    self.logger.log_compliance_event(
                        event_type="circuit_state_change",
                        event_data={"state": "open", "failures": self.failure_count},
                    )

    @property
    def is_open(self) -> bool:
        return self.state == "OPEN"

    def get_status(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout,
        }


class ToolCallTracer:
    """2025-standard tool call lifecycle tracing."""

    def __init__(self, config: EnterpriseLangSmithConfig) -> None:
        self.config = config
        self.pii_detector = config.pii_detector

    def create_tool_call_metadata(
        self,
        tool_calls_pending: list[Any],
        tool_outputs: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """Create privacy-safe tool call metadata for LangSmith."""

        session_hash = self.pii_detector.hash_session_id(session_id)

        tool_call_summary = {
            "session_hash": session_hash,
            "pending_tool_calls": len(tool_calls_pending),
            "completed_tool_calls": len(tool_outputs),
            "tool_types": list(
                {getattr(tc, "type", "unknown") for tc in tool_calls_pending}
            ),
            "tool_names": [
                tc.function.name
                for tc in tool_calls_pending
                if hasattr(tc, "function") and hasattr(tc.function, "name")
            ],
        }

        if tool_calls_pending:
            redacted_calls = []
            for tc in tool_calls_pending:
                if hasattr(tc, "function"):
                    args = getattr(tc.function, "arguments", "")
                    redacted_args = self.pii_detector.redact_pii(args) or ""
                    preview = redacted_args[:100]
                    if len(redacted_args) > 100:
                        preview += "..."
                    redacted_calls.append(
                        {
                            "tool_name": tc.function.name,
                            "arguments_preview": preview,
                            "status": getattr(tc, "status", "unknown"),
                        }
                    )
            tool_call_summary["tool_calls_detail"] = redacted_calls

        return tool_call_summary


class AgentReasoningTracer:
    """2025-standard agent reasoning transparency tracing."""

    def __init__(self, config: EnterpriseLangSmithConfig) -> None:
        self.config = config
        self.pii_detector = config.pii_detector

    def create_reasoning_metadata(
        self,
        agent_scratchpad: dict[str, list[str]],
        intermediate_steps: list[Any],
        agent_name: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Create privacy-safe reasoning metadata for LangSmith."""

        session_hash = self.pii_detector.hash_session_id(session_id)

        reasoning_summary = {
            "session_hash": session_hash,
            "agent_name": agent_name,
            "reasoning_steps_count": len(agent_scratchpad.get(agent_name, [])),
            "intermediate_steps_count": len(intermediate_steps),
            "reasoning_depth": "shallow" if len(intermediate_steps) < 3 else "deep",
        }

        if agent_name in agent_scratchpad:
            recent = agent_scratchpad[agent_name][-3:]
            redacted_reasoning = []
            for step in recent:
                redacted = self.pii_detector.redact_pii(step) or ""
                preview = redacted[:200]
                if len(redacted) > 200:
                    preview += "..."
                redacted_reasoning.append(preview)
            reasoning_summary["recent_reasoning_preview"] = redacted_reasoning

        if intermediate_steps:
            step_types = [
                getattr(step, "step_type", "unknown") for step in intermediate_steps
            ]
            reasoning_summary["step_types"] = list(set(step_types))

        return reasoning_summary


class CostTrackingIntegration:
    """2025-standard cost tracking integration with LangSmith."""

    def __init__(self, config: EnterpriseLangSmithConfig) -> None:
        self.config = config

    def create_cost_metadata(
        self,
        token_usage: Any,
        cost_tracking: Any,
        agent_name: str,
    ) -> dict[str, Any]:
        """Create cost attribution metadata for LangSmith."""

        cost_metadata = {
            "agent_name": agent_name,
            "session_total_tokens": getattr(token_usage, "total_tokens", 0),
            "session_total_cost_usd": getattr(cost_tracking, "total_cost_usd", 0.0),
            "cost_efficiency_score": self._calculate_efficiency_score(
                token_usage, cost_tracking
            ),
        }

        if (
            hasattr(token_usage, "agent_token_usage")
            and agent_name in token_usage.agent_token_usage
        ):
            agent_usage = token_usage.agent_token_usage[agent_name]
            cost_metadata.update(
                {
                    "agent_tokens": agent_usage.get("total_tokens", 0),
                    "agent_cost_usd": getattr(cost_tracking, "model_costs", {}).get(
                        agent_name, 0.0
                    ),
                    "agent_cost_per_token": self._calculate_cost_per_token(
                        agent_usage, cost_tracking
                    ),
                }
            )

        return cost_metadata

    def _calculate_efficiency_score(
        self, token_usage: Any, cost_tracking: Any
    ) -> float:
        total_tokens = getattr(token_usage, "total_tokens", 0)
        total_cost = getattr(cost_tracking, "total_cost_usd", 0.0)
        if total_tokens == 0 or total_cost == 0.0:
            return 0.0
        return total_tokens / max(total_cost, 0.001)

    def _calculate_cost_per_token(self, agent_usage: Any, cost_tracking: Any) -> float:
        tokens = int(agent_usage.get("total_tokens", 0))
        cost = float(
            getattr(cost_tracking, "model_costs", {}).get(
                agent_usage.get("agent_name"), 0.0
            )
        )
        if tokens == 0:
            return 0.0
        return cost / tokens


def create_enterprise_langsmith_client(
    config: EnterpriseLangSmithConfig,
) -> Client | None:
    """Create and validate an enterprise LangSmith client."""

    api_key = config.api_key
    if not api_key:
        get_safe_logger(__name__).info("langsmith_api_key_missing")
        return None

    try:
        client = Client(
            api_key=api_key,
            api_url=config.basic_config.get(
                "api_url", "https://api.smith.langchain.com"
            ),
        )
        try:
            client.list_projects(limit=1)
            get_safe_logger(__name__).info(
                "enterprise_langsmith_client_ready", project=config.project_name
            )
            return client
        except Exception as exc:  # noqa: BLE001
            get_safe_logger(__name__).error(
                "langsmith_client_validation_failed", error=str(exc)
            )
            return None
    except Exception as exc:  # noqa: BLE001
        get_safe_logger(__name__).error(
            "langsmith_client_creation_failed", error=str(exc)
        )
        return None


def setup_enterprise_langsmith_tracing(
    config_path: Path | str | None = None,
) -> EnterpriseLangSmithConfig:
    """Setup enterprise LangSmith tracing utilities."""

    config = EnterpriseLangSmithConfig(config_path)
    config._enterprise_client = create_enterprise_langsmith_client(config)

    get_safe_logger(__name__).info(
        "enterprise_langsmith_tracing_setup",
        environment=config.enterprise_settings.get("environment", "development"),
        sampling_rate=config.enterprise_settings.get("sampling_rate", 1.0),
        client_available=config._enterprise_client is not None,
    )

    return config


async def create_2025_standard_metadata(
    agent_name: str,
    session_id: str,
    state: Any,
    config: EnterpriseLangSmithConfig,
) -> dict[str, Any]:
    """Create enhanced LangSmith trace metadata."""

    base_metadata = config.create_privacy_safe_trace_metadata(agent_name, session_id)
    metadata = {
        **base_metadata,
        "agentic_ai_standard": "2025",
        "circuit_breaker_state": (
            config.circuit_breaker.state if config.circuit_breaker else "UNKNOWN"
        ),
    }

    if state is not None:
        if hasattr(state, "tool_calls_pending") or hasattr(state, "tool_outputs"):
            tracer = ToolCallTracer(config)
            metadata["tool_call_lifecycle"] = tracer.create_tool_call_metadata(
                getattr(state, "tool_calls_pending", []),
                getattr(state, "tool_outputs", {}),
                session_id,
            )

        if hasattr(state, "agent_scratchpad") or hasattr(state, "intermediate_steps"):
            r_tracer = AgentReasoningTracer(config)
            metadata["agent_reasoning"] = r_tracer.create_reasoning_metadata(
                getattr(state, "agent_scratchpad", {}),
                getattr(state, "intermediate_steps", []),
                agent_name,
                session_id,
            )

        if hasattr(state, "token_usage") or hasattr(state, "cost_tracking"):
            c_tracer = CostTrackingIntegration(config)
            metadata["cost_attribution"] = c_tracer.create_cost_metadata(
                getattr(state, "token_usage", None),
                getattr(state, "cost_tracking", None),
                agent_name,
            )

    return metadata


def enhance_trace_real_agent_execution(
    agent_name: str,
    session_id: str,
    enterprise_config: EnterpriseLangSmithConfig | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator adding enterprise LangSmith tracing with circuit breaker."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not enterprise_config or not enterprise_config.circuit_breaker:
                from .tracing import trace_real_agent_execution

                basic = trace_real_agent_execution(agent_name, session_id)
                return await basic(func)(*args, **kwargs)

            sampling_rate = enterprise_config.enterprise_settings.get(
                "sampling_rate", 1.0
            )
            if random.random() > sampling_rate:
                return await func(*args, **kwargs)

            start_time = time.perf_counter()

            state = next(
                (a for a in args if hasattr(a, "enterprise_trace_metadata")), None
            )

            try:
                async with enterprise_config.circuit_breaker:
                    metadata = await create_2025_standard_metadata(
                        agent_name, session_id, state, enterprise_config
                    )
                    from langsmith import traceable

                    @traceable(
                        name=f"enterprise_agent_{agent_name}",
                        project_name=enterprise_config.project_name,
                        metadata=metadata,
                        client=enterprise_config._enterprise_client,
                    )
                    async def _traced() -> Any:
                        return await func(*args, **kwargs)

                    result = await _traced()

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    await log_enterprise_performance_metrics(
                        enterprise_config,
                        agent_name,
                        session_id,
                        duration_ms,
                        state,
                        True,
                    )
                    return result
            except LangSmithCircuitBreakerError:
                duration_ms = (time.perf_counter() - start_time) * 1000
                await log_enterprise_performance_metrics(
                    enterprise_config,
                    agent_name,
                    session_id,
                    duration_ms,
                    state,
                    False,
                    "circuit_breaker_open",
                )
                return await func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                duration_ms = (time.perf_counter() - start_time) * 1000
                get_safe_logger(__name__).warning(
                    "enterprise_tracing_failed", error=str(exc)
                )
                await log_enterprise_performance_metrics(
                    enterprise_config,
                    agent_name,
                    session_id,
                    duration_ms,
                    state,
                    False,
                    f"langsmith_error:{exc}",
                )
                return await func(*args, **kwargs)

        return wrapper

    return decorator


async def log_enterprise_performance_metrics(
    config: EnterpriseLangSmithConfig,
    agent_name: str,
    session_id: str,
    execution_time_ms: float,
    state: Any,
    success: bool,
    fallback_reason: str | None = None,
) -> None:
    """Log execution metrics using PrivacySafeLogger."""

    logger = PrivacySafeLogger()
    data = {
        "agent_name": agent_name,
        "execution_time_ms": execution_time_ms,
        "overhead_target_ms": config.enterprise_settings.get(
            "max_trace_overhead_ms", 10.0
        ),
        "circuit_breaker_state": (
            config.circuit_breaker.state if config.circuit_breaker else "UNKNOWN"
        ),
        "success": success,
    }
    if fallback_reason:
        data["fallback_reason"] = fallback_reason

    if execution_time_ms > config.enterprise_settings.get(
        "max_trace_overhead_ms", 10.0
    ):
        get_safe_logger(__name__).warning(
            "enterprise_tracing_overhead_exceeded",
            actual_ms=execution_time_ms,
        )

    logger.log_session_event(session_id, f"enterprise_agent_{agent_name}", data)
