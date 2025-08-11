from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .modern_logger import ModernUniversalFrameworkLogger as UniversalFrameworkLogger


class LoggingContract(ABC):
    """Contract interface for all Universal Framework logging."""

    @abstractmethod
    def log_agent_execution(
        self,
        agent_name: str,
        session_id: str,
        execution_context: dict[str, Any],
        success: bool = True,
        error: str | None = None,
    ) -> None:
        pass

    @abstractmethod
    def log_workflow_transition(
        self,
        from_phase: str,
        to_phase: str,
        session_id: str,
        transition_context: dict[str, Any],
    ) -> None:
        pass

    @abstractmethod
    def log_compliance_event(
        self,
        event_type: str,
        event_data: dict[str, Any],
        session_id: str | None = None,
        privacy_level: str = "standard",
    ) -> None:
        pass


class LoggingFactory:
    """Factory for creating standardized loggers."""

    @staticmethod
    def create_agent_logger(agent_name: str) -> UniversalFrameworkLogger:
        return UniversalFrameworkLogger(f"agent_{agent_name}")

    @staticmethod
    def create_workflow_logger() -> UniversalFrameworkLogger:
        return UniversalFrameworkLogger("workflow_orchestrator")

    @staticmethod
    def create_compliance_logger() -> UniversalFrameworkLogger:
        return UniversalFrameworkLogger("compliance_manager")

    @staticmethod
    def create_observability_logger(name: str) -> UniversalFrameworkLogger:
        return UniversalFrameworkLogger(f"observability_{name}")
