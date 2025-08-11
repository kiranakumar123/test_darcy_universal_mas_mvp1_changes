"""LangSmith tracing integration for real agent execution."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

# Import feature flags to check safe mode before loading enterprise components
from ..config.feature_flags import feature_flags

# Conditionally import LangSmith and enterprise tracing only if enabled
if not feature_flags.is_safe_mode() and feature_flags.is_enabled("LANGSMITH_TRACING"):
    try:
        from langsmith import traceable

        from universal_framework.observability.enterprise_langsmith import (
            EnterpriseLangSmithConfig,
            enhance_trace_real_agent_execution,
        )

        _tracing_available = True
    except ImportError:
        _tracing_available = False
        traceable = None
        EnterpriseLangSmithConfig = None
        enhance_trace_real_agent_execution = None
else:
    # Safe mode - disable all tracing imports
    _tracing_available = False
    traceable = None
    EnterpriseLangSmithConfig = None
    enhance_trace_real_agent_execution = None


def trace_real_agent_execution(
    agent_name: str, node_name: str
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for comprehensive real agent tracing."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        @traceable(
            name=f"{node_name}_real_agent_execution",
            metadata={
                "agent_type": agent_name,
                "node_type": node_name,
                "execution_mode": "real_agent",
            },
        )
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception:
                raise

        return wrapper

    return decorator


def trace_agent_execution(
    agent_name: str,
    node_name: str,
    enterprise_config: Any | None = None,  # Use Any instead of conditional type
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Unified tracing decorator with optional enterprise features."""

    # If tracing is not available, return no-op decorator
    if not _tracing_available:

        def no_op_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return no_op_decorator

    if enterprise_config and enhance_trace_real_agent_execution:
        return enhance_trace_real_agent_execution(
            agent_name, node_name, enterprise_config
        )
    return trace_real_agent_execution(agent_name, node_name)
