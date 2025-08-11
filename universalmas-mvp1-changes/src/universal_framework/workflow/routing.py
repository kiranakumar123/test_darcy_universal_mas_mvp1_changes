"""Enhanced routing engine for Universal Multi-Agent System Framework."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase


class RoutingDecision(Enum):
    """Routing decision types."""

    CONTINUE_PHASE = "continue_phase"
    ADVANCE_PHASE = "advance_phase"
    ERROR_RECOVERY = "error_recovery"
    ESCALATE = "escalate"
    COMPLETE = "complete"


@dataclass(frozen=True)
class RoutingResult:
    """Result of routing decision."""

    next_node: str
    routing_reason: str
    decision_type: RoutingDecision
    recovery_path: str | None = None
    metadata: dict[str, Any] | None = None


class EnhancedWorkflowRouter:
    """Simplified enterprise-grade routing engine with circuit breaker."""

    def __init__(
        self,
        use_case_config: dict[str, Any] | None = None,
        performance_mode: bool = True,
    ) -> None:
        self.use_case_config = use_case_config or {}
        self.performance_mode = performance_mode
        self.routing_cache: dict[str, RoutingResult] = {}

        # Circuit breaker for infinite loop prevention
        self.node_visit_counts: dict[str, dict[str, int]] = (
            {}
        )  # session_id -> {node: count}
        self.max_node_visits = 3  # Reduced maximum visits to same node per session

        self.universal_agents = self._initialize_universal_agent_mapping()
        self.conditional_edges = self._create_conditional_edge_map()
        self.error_recovery_map = self._create_error_recovery_map()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def route_from_node(
        self,
        current_node: str,
        state: UniversalWorkflowState,
        error_context: dict[str, Any] | None = None,
    ) -> RoutingResult:
        """Determine next node with circuit breaker for infinite loop prevention."""

        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import (
            safe_get_phase,
            safe_get_session_id,
        )

        session_id = safe_get_session_id(state)
        if session_id not in self.node_visit_counts:
            self.node_visit_counts[session_id] = {}

        visit_count = self.node_visit_counts[session_id].get(current_node, 0)
        if visit_count >= self.max_node_visits:
            # Intelligent circuit breaker - force progression based on current phase
            current_phase = safe_get_phase(state)

            if current_phase == WorkflowPhase.BATCH_DISCOVERY:
                forced_next = "strategy_generator"
            elif current_phase == WorkflowPhase.STRATEGY_ANALYSIS:
                forced_next = "strategy_confirmation_handler"
            elif current_phase == WorkflowPhase.STRATEGY_CONFIRMATION:
                forced_next = "enhanced_email_generator"
            else:
                forced_next = "END"  # Complete workflow

            return RoutingResult(
                next_node=forced_next,
                routing_reason=f"Circuit breaker: {current_node} visited {visit_count} times, forcing progression",
                decision_type=RoutingDecision.ERROR_RECOVERY,
                recovery_path="forced_progression",
                metadata={
                    "circuit_breaker_triggered": True,
                    "visit_count": visit_count,
                    "forced_phase_progression": True,
                },
            )

        # Increment visit count
        self.node_visit_counts[session_id][current_node] = visit_count + 1

        cache_key = self._generate_cache_key(current_node, state, error_context)
        if self.performance_mode and cache_key in self.routing_cache:
            result = self.routing_cache[cache_key]
            if result.metadata is None:
                result = RoutingResult(
                    next_node=result.next_node,
                    routing_reason=result.routing_reason,
                    decision_type=result.decision_type,
                    recovery_path=result.recovery_path,
                    metadata={"cache_hit": True},
                )
            return result

        try:
            if error_context:
                routing_result = self._handle_error_recovery_routing(
                    current_node, state, error_context
                )
            else:
                routing_result = self._handle_standard_routing(current_node, state)

            if self.performance_mode:
                self.routing_cache[cache_key] = routing_result

            return routing_result
        except Exception as exc:  # noqa: BLE001
            return RoutingResult(
                next_node="failure_analyst",
                routing_reason=f"Routing system failure: {exc}",
                decision_type=RoutingDecision.ERROR_RECOVERY,
                recovery_path="escalation_handler",
            )

    def get_possible_next_nodes(self, node: str) -> list[str]:
        """Return possible next nodes for conditional edge mapping."""
        return self.conditional_edges.get(node, [])

    def reset_session_state(self, session_id: str) -> None:
        """Reset circuit breaker state for a session."""
        if session_id in self.node_visit_counts:
            del self.node_visit_counts[session_id]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _initialize_universal_agent_mapping(self) -> dict[str, dict[str, Any]]:
        """Initialize basic agent map."""
        return {
            "batch_requirements_collector": {"phase": WorkflowPhase.BATCH_DISCOVERY},
            "strategy_generator": {"phase": WorkflowPhase.STRATEGY_ANALYSIS},
            "strategy_confirmation_handler": {
                "phase": WorkflowPhase.STRATEGY_CONFIRMATION
            },
            "enhanced_email_generator": {"phase": WorkflowPhase.GENERATION},
        }

    def _create_conditional_edge_map(self) -> dict[str, list[str]]:
        """Create simple edge map for universal agents."""
        return {
            "batch_requirements_collector": ["email_workflow_orchestrator"],
            "strategy_generator": ["email_workflow_orchestrator"],
            "strategy_confirmation_handler": ["email_workflow_orchestrator"],
            "enhanced_email_generator": ["email_workflow_orchestrator"],
            "email_workflow_orchestrator": [
                "batch_requirements_collector",
                "strategy_generator",
                "strategy_confirmation_handler",
                "enhanced_email_generator",
                "END",
            ],
        }

    def _create_error_recovery_map(self) -> dict[str, dict[str, Any]]:
        """Basic error recovery configuration."""
        return {name: {"max_retries": 3} for name in self.universal_agents}

    def _generate_cache_key(
        self,
        node: str,
        state: UniversalWorkflowState,
        error: dict[str, Any] | None,
    ) -> str:
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import safe_get_phase

        workflow_phase = safe_get_phase(state)
        return f"{node}-{workflow_phase}-{bool(error)}"

    # ------------------------------------------------------------------
    # Routing logic
    # ------------------------------------------------------------------
    def _handle_standard_routing(
        self, current_node: str, state: UniversalWorkflowState
    ) -> RoutingResult:
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import safe_get_phase

        current_phase = safe_get_phase(state)

        match current_phase:
            case WorkflowPhase.INITIALIZATION:
                return RoutingResult(
                    next_node="batch_requirements_collector",
                    routing_reason="start discovery",
                    decision_type=RoutingDecision.ADVANCE_PHASE,
                )
            case WorkflowPhase.BATCH_DISCOVERY:
                return RoutingResult(
                    next_node="strategy_generator",
                    routing_reason="requirements collected",
                    decision_type=RoutingDecision.ADVANCE_PHASE,
                )
            case WorkflowPhase.STRATEGY_ANALYSIS:
                return RoutingResult(
                    next_node="strategy_confirmation_handler",
                    routing_reason="strategy ready",
                    decision_type=RoutingDecision.ADVANCE_PHASE,
                )
            case WorkflowPhase.STRATEGY_CONFIRMATION:
                return RoutingResult(
                    next_node="enhanced_email_generator",
                    routing_reason="strategy confirmed",
                    decision_type=RoutingDecision.ADVANCE_PHASE,
                )
            case WorkflowPhase.GENERATION:
                return RoutingResult(
                    next_node="END",
                    routing_reason="generation complete",
                    decision_type=RoutingDecision.COMPLETE,
                )
            case _:
                return RoutingResult(
                    next_node="failure_analyst",
                    routing_reason=f"Unknown phase: {current_phase}",
                    decision_type=RoutingDecision.ERROR_RECOVERY,
                )

    def _handle_error_recovery_routing(
        self,
        failed_node: str,
        state: UniversalWorkflowState,
        error_context: dict[str, Any],
    ) -> RoutingResult:
        retry_count = error_context.get("retry_count", 0)
        recovery_conf = self.error_recovery_map.get(failed_node, {"max_retries": 3})
        if retry_count >= recovery_conf.get("max_retries", 3):
            return RoutingResult(
                next_node="escalation_handler",
                routing_reason=f"Max retries exceeded for {failed_node}",
                decision_type=RoutingDecision.ESCALATE,
                recovery_path="human_intervention",
            )
        return RoutingResult(
            next_node="failure_analyst",
            routing_reason=f"Recovery for {failed_node}",
            decision_type=RoutingDecision.ERROR_RECOVERY,
            recovery_path=failed_node,
        )
