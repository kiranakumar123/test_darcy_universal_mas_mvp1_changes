"""Workflow state contract definitions for the streamlined workflow."""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from universal_framework.compliance import FailClosedStateValidator

# Compliance context for automatic state validation
_COMPLIANCE_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar(
    "_COMPLIANCE_CONTEXT", default=None
)


def set_compliance_context(context: dict[str, Any] | None) -> ContextVar.Token:
    """Set compliance context for state mutations."""

    return _COMPLIANCE_CONTEXT.set(context)


def reset_compliance_context(token: ContextVar.Token) -> None:
    """Reset compliance context to previous value."""

    _COMPLIANCE_CONTEXT.reset(token)


def get_compliance_context() -> dict[str, Any] | None:
    """Get current compliance context if available."""

    return _COMPLIANCE_CONTEXT.get()


"""
Checkpoint Dictionary Structure:
{
    "node": str,
    "timestamp": str,
    "phase": WorkflowPhase,
    "completion": Dict[str, float],
    "context": Dict[str, Any],  # Optional context snapshot
    "metadata": Dict[str, Any],  # Optional additional metadata
}
"""


class WorkflowPhase(str, Enum):
    """Allowed workflow phases."""

    INITIALIZATION = "initialization"
    BATCH_DISCOVERY = "batch_discovery"
    STRATEGY_ANALYSIS = "strategy_analysis"
    STRATEGY_CONFIRMATION = "strategy_confirmation"
    GENERATION = "generation"
    REVIEW = "review"
    DELIVERY = "delivery"


class EmailRequirements(BaseModel):
    """Batch collected email requirements."""

    purpose: str = Field(..., min_length=10)
    email_type: Literal[
        "announcement",
        "update",
        "request",
        "reminder",
        "follow_up",
    ] = "update"
    audience: list[str] = Field(..., min_items=1)  # type: ignore[call-overload]
    tone: Literal[
        "professional",
        "casual",
        "urgent",
        "enthusiastic",
        "professional_enthusiastic",
    ]
    key_messages: list[str] = Field(..., min_items=1, max_items=10)  # type: ignore[call-overload]
    call_to_action: str | None = None
    company_context: dict[str, str] = Field(default_factory=dict)
    additional_preferences: str | None = None
    completeness_score: float = Field(0.0, ge=0.0, le=1.0)
    missing_info: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class EmailStrategy(BaseModel):
    """Generated email strategy with confirmation status."""

    overall_approach: str
    tone_strategy: str
    structure_strategy: list[str]
    messaging_strategy: dict[str, Any]
    personalization_strategy: dict[str, str]
    estimated_impact: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)

    # Fields for enhanced generation
    subject: str = ""
    content: str = ""
    target_audience: str = ""
    tone: str = ""
    call_to_action: str = ""
    is_confirmed: bool = False
    approach: str = ""
    key_messages: list[str] = Field(default_factory=list)
    timing_considerations: str = ""
    success_metrics: str = ""

    model_config = ConfigDict(frozen=True)


class ConflictAnalysis(BaseModel):
    """Strategy vs user preference conflict analysis."""

    has_conflicts: bool
    conflicts: list[dict[str, str]] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    requires_user_confirmation: bool = False

    model_config = ConfigDict(frozen=True)


class GeneratedEmail(BaseModel):
    """Complete email output details."""

    subject: str = Field(..., min_length=3, max_length=120)
    html_content: str = Field(..., min_length=20)
    text_content: str = Field(..., min_length=10)
    quality_score: float = Field(..., ge=0.0, le=1.0)
    template_used: str = Field(..., min_length=1)
    personalization_applied: dict[str, str]
    brand_compliance_score: float = Field(..., ge=0.0, le=1.0)
    strategy_applied: str = Field(..., min_length=1)


class ValidationResult(BaseModel):
    """Results of generation validation."""

    is_approved: bool
    quality_scores: dict[str, float]
    issues: list[str]
    improvement_suggestions: list[str] | None = None


class UniversalWorkflowState(BaseModel):
    """Immutable state for the streamlined workflow."""

    session_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    user_id: str = Field(..., min_length=1)
    auth_token: str = Field(..., min_length=10)
    workflow_phase: WorkflowPhase = WorkflowPhase.INITIALIZATION
    previous_phase: WorkflowPhase | None = None
    phase_completion: dict[str, float] = Field(default_factory=dict)
    can_advance: bool = False
    messages: list[BaseMessage] = Field(default_factory=list)
    # See ``Checkpoint Dictionary Structure`` below for required keys
    conversation_checkpoints: list[dict[str, Any]] = Field(default_factory=list)
    email_requirements: EmailRequirements | None = None
    email_strategy: EmailStrategy | None = None
    conflict_analysis: ConflictAnalysis | None = None
    strategy_approved: bool = False
    generated_outputs: dict[str, Any] = Field(default_factory=dict)
    component_outputs: dict[str, Any] = Field(default_factory=dict)
    component_status: dict[str, str] = Field(default_factory=dict)
    validation_results: dict[str, Any] = Field(default_factory=dict)
    final_outputs: dict[str, Any] = Field(default_factory=dict)
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)
    context_data: dict[str, Any] = Field(default_factory=dict)
    error_info: dict[str, str] | None = None

    # Fields for enhanced error recovery and routing
    error_recovery_state: dict[str, Any] = Field(default_factory=dict)
    routing_history: list[dict[str, Any]] = Field(default_factory=list)
    escalation_count: int = 0
    recovery_attempts: dict[str, int] = Field(default_factory=dict)
    circuit_breaker_states: dict[str, str] = Field(default_factory=dict)
    last_successful_checkpoint: str | None = None
    performance_warnings: list[dict[str, Any]] = Field(default_factory=list)

    # Fields for enterprise LangSmith observability
    enterprise_trace_metadata: dict[str, Any] = Field(default_factory=dict)
    langsmith_circuit_breaker_state: str = "CLOSED"
    tool_call_trace_ids: dict[str, str] = Field(default_factory=dict)
    reasoning_trace_correlation: dict[str, str] = Field(default_factory=dict)
    cost_trace_metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)

    def transition_to_phase(self, new_phase: WorkflowPhase) -> UniversalWorkflowState:
        """Return new state with updated workflow phase and previous tracking."""
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import (
            safe_get,
            safe_get_phase_completion,
        )

        current_phase_completion = safe_get_phase_completion(self)
        current_workflow_phase = safe_get(
            self, "workflow_phase", WorkflowPhase, WorkflowPhase.INITIALIZATION
        )

        return self.copy(
            update={
                "previous_phase": current_workflow_phase,
                "workflow_phase": new_phase,
                "phase_completion": {**current_phase_completion, new_phase.value: 0.0},
            }
        )

    def has_phase_transition(self) -> bool:
        """Return True if state represents an actual phase transition."""
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import safe_get

        previous_phase = safe_get(self, "previous_phase", WorkflowPhase)
        workflow_phase = safe_get(
            self, "workflow_phase", WorkflowPhase, WorkflowPhase.INITIALIZATION
        )

        return previous_phase is not None and previous_phase != workflow_phase

    def get_transition_context(self) -> dict[str, str]:
        """Return transition context for audit logging."""
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import safe_get

        previous_phase = safe_get(self, "previous_phase", WorkflowPhase)
        workflow_phase = safe_get(
            self, "workflow_phase", WorkflowPhase, WorkflowPhase.INITIALIZATION
        )
        session_id = safe_get(self, "session_id", str, "")

        if not self.has_phase_transition():
            return {}
        return {
            "from_phase": previous_phase.value if previous_phase else "",
            "to_phase": workflow_phase.value,
            "transition_timestamp": datetime.now().isoformat(),
            "session_id": session_id,
        }

    def copy(
        self,
        update: dict[str, Any] | None = None,
        *,
        source_agent: str | None = None,
        event: str | None = None,
        validator: FailClosedStateValidator | None = None,
    ) -> UniversalWorkflowState:
        """Return updated copy with automatic compliance validation."""

        if update is None:
            update = {}

        if validator is None or source_agent is None or event is None:
            ctx = get_compliance_context()
            if ctx:
                validator = validator or ctx.get("validator")
                source_agent = source_agent or ctx.get("source_agent")
                event = event or ctx.get("event")

        if validator and source_agent and event:
            try:
                return validator.validate_state_update(
                    state=self,
                    updates=update,
                    source_agent=source_agent,
                    event=event,
                    user_context=get_compliance_context() or {},
                )
            except Exception as exc:  # noqa: BLE001
                exc.add_note(
                    "Compliance validation failed - "
                    f"Source: {source_agent}, Event: {event}, "
                    f"Updates: {list(update.keys())}"
                )
                raise

        return self.model_copy(update=update)

    def update_requirements(
        self, requirements: EmailRequirements
    ) -> UniversalWorkflowState:
        """Return updated state with new requirements."""
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import safe_get_phase_completion

        current_phase_completion = safe_get_phase_completion(self)

        next_phase = (
            WorkflowPhase.STRATEGY_ANALYSIS
            if requirements.completeness_score >= 0.8
            else WorkflowPhase.BATCH_DISCOVERY
        )
        return self.copy(
            update={
                "email_requirements": requirements,
                "workflow_phase": next_phase,
                "phase_completion": {
                    **current_phase_completion,
                    "discovery": requirements.completeness_score,
                },
            }
        )

    def update_strategy(
        self, strategy: EmailStrategy, conflicts: ConflictAnalysis
    ) -> UniversalWorkflowState:
        """Return updated state with strategy and conflict analysis."""
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import safe_get_phase_completion

        current_phase_completion = safe_get_phase_completion(self)

        next_phase = (
            WorkflowPhase.STRATEGY_CONFIRMATION
            if conflicts.has_conflicts
            else WorkflowPhase.GENERATION
        )
        return self.copy(
            update={
                "email_strategy": strategy,
                "conflict_analysis": conflicts,
                "workflow_phase": next_phase,
                "phase_completion": {
                    **current_phase_completion,
                    "strategy": strategy.confidence_score,
                },
            }
        )

    def approve_strategy(self, approved: bool) -> UniversalWorkflowState:
        """Return updated state based on strategy approval."""
        return self.copy(
            update={
                "strategy_approved": approved,
                "workflow_phase": (
                    WorkflowPhase.GENERATION
                    if approved
                    else WorkflowPhase.STRATEGY_ANALYSIS
                ),
            }
        )

    def add_checkpoint(
        self,
        node: str,
        phase: WorkflowPhase,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add workflow checkpoint for navigation and audit trail."""
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import safe_get_phase_completion

        phase_completion = safe_get_phase_completion(self).copy()

        checkpoint = {
            "node": node,
            "phase": phase.value if hasattr(phase, "value") else str(phase),
            "timestamp": datetime.now().isoformat(),
            "completion": phase_completion,
            "metadata": metadata or {},
        }

        # Use defensive access for conversation_checkpoints
        checkpoints = getattr(self, "conversation_checkpoints", [])
        if not isinstance(checkpoints, list):
            checkpoints = []
        checkpoints.append(checkpoint)

        # Note: This method should not modify state in-place, but for backward compatibility
        # we'll update the attribute if it exists
        if hasattr(self, "conversation_checkpoints"):
            self.conversation_checkpoints = checkpoints
        elif isinstance(self, dict):
            self["conversation_checkpoints"] = checkpoints


class BatchCollectionResponse(BaseModel):
    """UI response for batch information collection."""

    message: str
    collection_progress: dict[str, str]
    missing_requirements: list[str]
    completion_percentage: float
    next_action: Literal["continue_collection", "proceed_to_strategy"]

    model_config = ConfigDict(frozen=True)


class StrategyPresentationResponse(BaseModel):
    """UI response for strategy presentation."""

    message: str
    strategy_summary: dict[str, str]
    conflict_detected: bool
    user_options: list[str]
    strategy_confidence: float

    model_config = ConfigDict(frozen=True)


class GenerationProgressResponse(BaseModel):
    """UI response during email generation."""

    message: str
    generation_status: Literal["planning", "generating", "validating", "complete"]
    progress_percentage: float
    estimated_completion: str

    model_config = ConfigDict(frozen=True)


class EmailDeliveryResponse(BaseModel):
    """UI response for final email delivery."""

    message: str
    email_preview: str
    quality_metrics: dict[str, float]
    available_actions: list[str]
    export_options: list[str]

    model_config = ConfigDict(frozen=True)
