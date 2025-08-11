from __future__ import annotations

from typing import Any

"""
Performance logging utility for Universal Framework
"""
from .modern_logger import ModernUniversalFrameworkLogger as UniversalFrameworkLogger


class PerformanceLogger:
    """Performance monitoring with enterprise integration."""

    def __init__(self) -> None:
        self.logger = UniversalFrameworkLogger("performance_monitor")

    def log_agent_performance(
        self,
        agent_name: str,
        execution_time_ms: float,
        session_id: str,
        context: dict[str, Any],
    ) -> None:
        if execution_time_ms > 500:
            self.logger.log_error(
                error_type="performance_violation",
                error_message=f"Agent {agent_name} exceeded 500ms threshold: {execution_time_ms}ms",
                session_id=session_id,
                context={
                    "agent_name": agent_name,
                    "execution_time_ms": execution_time_ms,
                },
            )
        self.logger.log_performance_metric(
            metric_name="agent_execution_time_ms",
            metric_value=execution_time_ms,
            context={
                "agent_name": agent_name,
                "session_hash": self.logger.privacy_logger.pii_detector.hash_session_id(
                    session_id
                ),
                **context,
            },
        )

    def log_workflow_performance(
        self,
        workflow_phase: str,
        phase_duration_ms: float,
        session_id: str,
        phase_context: dict[str, Any],
    ) -> None:
        self.logger.log_performance_metric(
            metric_name="workflow_phase_duration_ms",
            metric_value=phase_duration_ms,
            context={
                "workflow_phase": workflow_phase,
                "session_hash": self.logger.privacy_logger.pii_detector.hash_session_id(
                    session_id
                ),
                **phase_context,
            },
        )
