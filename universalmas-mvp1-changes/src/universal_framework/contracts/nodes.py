"""Streamlined node interface contracts and utilities."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

# Use TYPE_CHECKING to prevent circular imports
if TYPE_CHECKING:
    pass

from universal_framework.config.feature_flags import feature_flags
from universal_framework.contracts.state import (
    BatchCollectionResponse,
    EmailDeliveryResponse,
    GenerationProgressResponse,
    StrategyPresentationResponse,
    UniversalWorkflowState,
    WorkflowPhase,
    get_compliance_context,
    reset_compliance_context,
    set_compliance_context,
)


class NodeContract(Protocol):
    """Protocol for async workflow node functions."""

    async def __call__(self, state: UniversalWorkflowState) -> UniversalWorkflowState:
        """Process and return workflow state."""
        raise NotImplementedError


T = TypeVar("T", bound=NodeContract)


# Lazy import functions to prevent circular imports
def _get_compliance_classes():
    """Lazy import compliance classes to prevent circular imports."""
    from universal_framework.compliance import (
        EnterpriseAuditManager,
        FailClosedStateValidator,
        PrivacySafeLogger,
    )

    return EnterpriseAuditManager, FailClosedStateValidator, PrivacySafeLogger


# Global validator registry per workflow
_validator_registry: dict[str, Any] = {}  # Use Any to avoid type import issues


def register_validator(workflow_id: str, validator: Any) -> None:
    """Register validator for a workflow instance."""
    _validator_registry[workflow_id] = validator


def get_validator(workflow_id: str) -> Any | None:
    """Retrieve registered validator for workflow."""
    return _validator_registry.get(workflow_id)


async def format_response_for_phase(
    state: UniversalWorkflowState,
    formatter: str,
    node_name: str,
) -> (
    BatchCollectionResponse
    | StrategyPresentationResponse
    | GenerationProgressResponse
    | EmailDeliveryResponse
):
    """Return a UI response model for the state's current phase."""
    # Defensive programming for LangGraph state conversion
    workflow_phase = (
        state.workflow_phase
        if hasattr(state, "workflow_phase")
        else WorkflowPhase(
            state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
        )
    )

    if workflow_phase == WorkflowPhase.BATCH_DISCOVERY:
        # Defensive programming for LangGraph state conversion
        try:
            phase_completion = state.phase_completion
        except AttributeError:
            phase_completion = (
                state.get("phase_completion", {}) if isinstance(state, dict) else {}
            )

        return BatchCollectionResponse(
            message="Collecting batch requirements...",
            collection_progress={},
            missing_requirements=[],
            completion_percentage=phase_completion.get("discovery", 0.0),
            next_action="continue_collection",
        )
    if workflow_phase == WorkflowPhase.STRATEGY_CONFIRMATION:
        return StrategyPresentationResponse(
            message="Please confirm your email strategy.",
            strategy_summary={},
            conflict_detected=(
                state.conflict_analysis.has_conflicts
                if state.conflict_analysis
                else False
            ),
            user_options=["approve", "modify", "reject"],
            strategy_confidence=(
                state.email_strategy.confidence_score if state.email_strategy else 0.0
            ),
        )
    if workflow_phase == WorkflowPhase.GENERATION:
        # Defensive programming for LangGraph state conversion
        try:
            phase_completion = state.phase_completion
        except AttributeError:
            phase_completion = (
                state.get("phase_completion", {}) if isinstance(state, dict) else {}
            )

        return GenerationProgressResponse(
            message="Generating your email...",
            generation_status="generating",
            progress_percentage=phase_completion.get("generation", 0.0),
            estimated_completion="soon",
        )
    if workflow_phase == WorkflowPhase.DELIVERY:
        return EmailDeliveryResponse(
            message="Here is your generated email.",
            email_preview="",
            quality_metrics={},
            available_actions=["view_full_email", "export"],
            export_options=["html", "text"],
        )
    return BatchCollectionResponse(
        message=f"Processing in {workflow_phase.value} phase...",
        collection_progress={},
        missing_requirements=[],
        completion_percentage=0.0,
        next_action="continue_collection",
    )


def check_state_transition(
    old_state: UniversalWorkflowState, new_state: UniversalWorkflowState
) -> bool:
    """Return True if state progresses or stays in the same phase."""
    phases = list(WorkflowPhase)
    # Defensive programming for LangGraph state conversion
    new_workflow_phase = (
        new_state.workflow_phase
        if hasattr(new_state, "workflow_phase")
        else WorkflowPhase(
            new_state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
        )
    )
    old_workflow_phase = (
        old_state.workflow_phase
        if hasattr(old_state, "workflow_phase")
        else WorkflowPhase(
            old_state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
        )
    )

    return phases.index(new_workflow_phase) >= phases.index(old_workflow_phase)


def check_required_fields(state: UniversalWorkflowState) -> bool:
    """Ensure required fields for each phase are present."""
    # Defensive programming for LangGraph state conversion
    workflow_phase = (
        state.workflow_phase
        if hasattr(state, "workflow_phase")
        else WorkflowPhase(
            state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
        )
    )

    missing_reqs = (
        workflow_phase
        in {
            WorkflowPhase.STRATEGY_ANALYSIS,
            WorkflowPhase.STRATEGY_CONFIRMATION,
            WorkflowPhase.GENERATION,
            WorkflowPhase.REVIEW,
            WorkflowPhase.DELIVERY,
        }
        and state.email_requirements is None
    )
    missing_strategy = (
        workflow_phase
        in {
            WorkflowPhase.STRATEGY_CONFIRMATION,
            WorkflowPhase.GENERATION,
            WorkflowPhase.REVIEW,
            WorkflowPhase.DELIVERY,
        }
        and state.email_strategy is None
    )
    return not (missing_reqs or missing_strategy)


def check_data_quality(state: UniversalWorkflowState) -> bool:
    """Validate numeric ranges for phase completion data."""
    # Defensive programming for LangGraph state conversion
    try:
        phase_completion = state.phase_completion
    except AttributeError:
        phase_completion = state.get("phase_completion", {})

    return all(0.0 <= value <= 1.0 for value in phase_completion.values())


async def validate_streamlined_logic(
    node_name: str, old_state: UniversalWorkflowState, new_state: UniversalWorkflowState
) -> dict[str, Any]:
    """Perform basic validation checks on a state transition."""
    validation_checks = {
        "state_transition_valid": check_state_transition(old_state, new_state),
        "required_fields_present": check_required_fields(new_state),
        "data_quality_acceptable": check_data_quality(new_state),
    }
    return {"is_valid": all(validation_checks.values()), "checks": validation_checks}


async def apply_streamlined_corrections(
    state: UniversalWorkflowState, reflection_result: dict[str, Any]
) -> UniversalWorkflowState:
    """Placeholder for applying corrections based on reflection results."""
    return state


def route_streamlined_error(
    state: UniversalWorkflowState, node_name: str, error: str, fallback_strategy: str
) -> UniversalWorkflowState:
    """Attach error details and return a new state instance."""
    return state.copy(
        update={
            "error_info": {
                "node": node_name,
                "error": error,
                "fallback": fallback_strategy,
            }
        }
    )


def streamlined_node(
    node_name: str,
    phase: WorkflowPhase,
    response_formatter: str = "default",
    fallback_strategy: str = "retry",
) -> Callable[[T], T]:
    """Decorate a node to enforce phase, auditing, and error handling."""

    def decorator(node_func: T) -> T:
        @wraps(node_func)
        async def wrapper(state: UniversalWorkflowState) -> UniversalWorkflowState:
            # Use lazy imports to prevent circular dependencies
            EnterpriseAuditManager, FailClosedStateValidator, PrivacySafeLogger = (
                _get_compliance_classes()
            )

            logger: Any = getattr(wrapper, "_privacy_logger", None)
            if logger is None:
                logger = PrivacySafeLogger()

            audit_mgr: Any = getattr(wrapper, "_audit_manager", None)
            if audit_mgr is None:
                if feature_flags.is_enabled("ENTERPRISE_FEATURES"):
                    from ..observability.enterprise_langsmith import (
                        EnterpriseLangSmithConfig,
                    )

                    langsmith_config = EnterpriseLangSmithConfig()
                    audit_mgr = EnterpriseAuditManager(logger, langsmith_config)
                else:
                    # Safe mode - use minimal audit interface
                    from ..compliance.safe_mode import SafeModeAuditManager

                    audit_mgr = SafeModeAuditManager()
            cast(Any, wrapper)._privacy_logger = logger
            cast(Any, wrapper)._audit_manager = audit_mgr

            validator: Any = getattr(wrapper, "_validator", None)
            token = None
            if validator:
                token = set_compliance_context(
                    {
                        "validator": validator,
                        "source_agent": node_name,
                        "event": f"{node_name}_execution",
                    }
                )

            start_time = datetime.now()
            # Defensive programming for LangGraph state conversion
            state_workflow_phase = (
                state.workflow_phase
                if hasattr(state, "workflow_phase")
                else WorkflowPhase(
                    state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
                )
            )

            # Allow phase transitions for certain nodes - strategy_generator can be called
            # during BATCH_DISCOVERY -> STRATEGY_ANALYSIS transition
            valid_phases = [phase]
            if (
                node_name == "strategy_generator"
                and phase == WorkflowPhase.STRATEGY_ANALYSIS
            ):
                valid_phases.append(WorkflowPhase.BATCH_DISCOVERY)  # Allow transition
            elif (
                node_name == "strategy_confirmation_handler"
                and phase == WorkflowPhase.STRATEGY_CONFIRMATION
            ):
                valid_phases.append(WorkflowPhase.STRATEGY_ANALYSIS)  # Allow transition
            elif (
                node_name == "enhanced_email_generator"
                and phase == WorkflowPhase.GENERATION
            ):
                valid_phases.append(
                    WorkflowPhase.STRATEGY_CONFIRMATION
                )  # Allow transition

            if (
                state_workflow_phase not in valid_phases
                and phase != WorkflowPhase.INITIALIZATION
            ):
                raise ValueError(
                    f"Node {node_name} expected phase {phase}, "
                    f"got {state_workflow_phase}"
                )

            execution_id = f"{node_name}_{start_time.timestamp()}"
            # Defensive programming for LangGraph state conversion
            session_id = (
                state.session_id
                if hasattr(state, "session_id")
                else state.get("session_id", "unknown")
            )
            actual_phase_value = (
                state.workflow_phase.value
                if hasattr(state, "workflow_phase")
                else state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
            )

            audit_entry: dict[str, Any] = {
                "execution_id": execution_id,
                "node_name": node_name,
                "expected_phase": phase.value,
                "actual_phase": actual_phase_value,
                "session_id": session_id,
                "timestamp_start": start_time.isoformat(),
            }

            checkpoint_metadata = {
                "start_time": start_time.isoformat(),
                "agent_function": getattr(node_func, "__name__", node_name),
                "execution_id": execution_id,
            }
            state.add_checkpoint(node_name, phase, checkpoint_metadata)

            try:
                result_state = await node_func(state)
                if not isinstance(result_state, UniversalWorkflowState):
                    raise TypeError(f"Node {node_name} returned invalid state type")

                ui_response = await format_response_for_phase(
                    result_state, response_formatter, node_name
                )

                # Defensive programming for LangGraph state conversion
                result_state_context_data = (
                    result_state.context_data
                    if hasattr(result_state, "context_data")
                    else result_state.get("context_data", {})
                )

                result_state = result_state.copy(
                    update={
                        "context_data": {
                            **result_state_context_data,
                            "ui_response": ui_response.model_dump(),
                        }
                    }
                )

                if node_name in ["batch_requirements_collector", "strategy_generator"]:
                    reflection_result = await validate_streamlined_logic(
                        node_name, state, result_state
                    )
                    if not reflection_result.get("is_valid", True):
                        result_state = await apply_streamlined_corrections(
                            result_state, reflection_result
                        )

                # Defensive programming for LangGraph state conversion
                result_state_workflow_phase_value = (
                    result_state.workflow_phase.value
                    if hasattr(result_state, "workflow_phase")
                    else result_state.get(
                        "workflow_phase", WorkflowPhase.INITIALIZATION.value
                    )
                )

                audit_entry.update(
                    {
                        "status": "success",
                        "output_phase": result_state_workflow_phase_value,
                        "timestamp_end": datetime.now().isoformat(),
                    }
                )

                # Defensive programming for LangGraph state conversion
                try:
                    result_phase_completion = result_state.phase_completion
                except AttributeError:
                    result_phase_completion = (
                        result_state.get("phase_completion", {})
                        if isinstance(result_state, dict)
                        else {}
                    )

                performance_metrics = {
                    "execution_time_seconds": (
                        datetime.now() - start_time
                    ).total_seconds(),
                    "phase_completion": result_phase_completion.get(phase.value, 0.0),
                }

                # Defensive programming for LangGraph state conversion
                execution_session_id = (
                    state.session_id
                    if hasattr(state, "session_id")
                    else state.get("session_id", "unknown")
                )

                execution_context = {
                    "node_name": node_name,
                    "phase": phase.value,
                    "start_time": start_time.isoformat(),
                    "session_id": execution_session_id,
                }

                audit_mgr.track_agent_execution(
                    agent_name=node_name,
                    session_id=execution_session_id,
                    execution_context=execution_context,
                    performance_metrics=performance_metrics,
                    success=True,
                )

                if state.conversation_checkpoints:
                    completion_time = datetime.now()
                    duration = (completion_time - start_time).total_seconds()
                    last_checkpoint = state.conversation_checkpoints[-1]
                    last_checkpoint["metadata"].update(
                        {
                            "completion_time": completion_time.isoformat(),
                            "execution_duration_seconds": duration,
                            "status": "completed",
                            "success": True,
                        }
                    )

                return result_state

            except Exception as exc:  # noqa: BLE001
                audit_entry.update(
                    {
                        "status": "error",
                        "error": str(exc),
                        "fallback_strategy": fallback_strategy,
                        "timestamp_end": datetime.now().isoformat(),
                    }
                )
                if state.conversation_checkpoints:
                    completion_time = datetime.now()
                    duration = (completion_time - start_time).total_seconds()
                    last_checkpoint = state.conversation_checkpoints[-1]
                    last_checkpoint["metadata"].update(
                        {
                            "completion_time": completion_time.isoformat(),
                            "execution_duration_seconds": duration,
                            "status": "failed",
                            "success": False,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        }
                    )

                performance_metrics = {
                    "execution_time_seconds": (
                        datetime.now() - start_time
                    ).total_seconds()
                }

                # Defensive programming for LangGraph state conversion
                error_session_id = (
                    state.session_id
                    if hasattr(state, "session_id")
                    else state.get("session_id", "unknown")
                )

                execution_context = {
                    "node_name": node_name,
                    "phase": phase.value,
                    "start_time": start_time.isoformat(),
                    "session_id": error_session_id,
                }

                audit_mgr.track_agent_execution(
                    agent_name=node_name,
                    session_id=error_session_id,
                    execution_context=execution_context,
                    performance_metrics=performance_metrics,
                    success=False,
                    error_message=str(exc),
                )

                raise

            finally:
                if token:
                    reset_compliance_context(token)

        return cast(T, wrapper)

    return decorator


def get_checkpoint_summary(state: UniversalWorkflowState) -> dict[str, Any]:
    """Get summary statistics for workflow checkpoints."""
    # Defensive programming for LangGraph state conversion
    conversation_checkpoints = (
        state.conversation_checkpoints
        if hasattr(state, "conversation_checkpoints")
        else state.get("conversation_checkpoints", [])
    )

    if not conversation_checkpoints:
        return {
            "total_checkpoints": 0,
            "completed_checkpoints": 0,
            "failed_checkpoints": 0,
            "average_execution_time": 0.0,
            "last_checkpoint": None,
        }

    checkpoints = conversation_checkpoints
    completed = sum(
        1 for cp in checkpoints if cp.get("metadata", {}).get("status") == "completed"
    )
    failed = sum(
        1 for cp in checkpoints if cp.get("metadata", {}).get("status") == "failed"
    )
    execution_times = [
        cp.get("metadata", {}).get("execution_duration_seconds", 0)
        for cp in checkpoints
        if cp.get("metadata", {}).get("execution_duration_seconds") is not None
    ]
    avg_time = sum(execution_times) / len(execution_times) if execution_times else 0.0

    return {
        "total_checkpoints": len(checkpoints),
        "completed_checkpoints": completed,
        "failed_checkpoints": failed,
        "average_execution_time": avg_time,
        "last_checkpoint": checkpoints[-1] if checkpoints else None,
        "success_rate": completed / len(checkpoints) if checkpoints else 0.0,
    }


def validate_checkpoint_integrity(state: UniversalWorkflowState) -> list[str]:
    """Validate checkpoint data integrity for audit compliance."""
    errors = []

    # Defensive programming for LangGraph state conversion
    conversation_checkpoints = (
        state.conversation_checkpoints
        if hasattr(state, "conversation_checkpoints")
        else state.get("conversation_checkpoints", [])
    )

    if not conversation_checkpoints:
        errors.append("Missing conversation_checkpoints attribute")
        return errors

    for idx, checkpoint in enumerate(conversation_checkpoints):
        checkpoint_id = f"checkpoint_{idx}"
        for field in ["node", "phase", "timestamp"]:
            if field not in checkpoint:
                errors.append(f"{checkpoint_id}: Missing required field '{field}'")

        metadata = checkpoint.get("metadata", {})
        if metadata.get("status") == "completed":
            if "completion_time" not in metadata:
                errors.append(
                    f"{checkpoint_id}: Completed checkpoint missing completion_time"
                )
            if "execution_duration_seconds" not in metadata:
                errors.append(
                    f"{checkpoint_id}: Completed checkpoint missing execution_duration_seconds"
                )

        try:
            datetime.fromisoformat(checkpoint.get("timestamp", ""))
        except (ValueError, TypeError):
            errors.append(f"{checkpoint_id}: Invalid timestamp format")

    return errors


def update_state_with_compliance(
    state: UniversalWorkflowState,
    updates: dict[str, Any],
    source_agent: str,
    event: str,
    validator: Any = None,
) -> UniversalWorkflowState:
    """Return updated state using optional explicit compliance validation."""

    return state.copy(
        update=updates,
        source_agent=source_agent,
        event=event,
        validator=validator,
    )


def get_current_compliance_context() -> dict[str, Any] | None:
    """Return current compliance context for debugging."""

    return get_compliance_context()


def is_compliance_active() -> bool:
    """Return True if compliance validation is currently active."""

    ctx = get_compliance_context()
    return bool(ctx and ctx.get("validator"))


def validate_compliance_context() -> dict[str, Any]:
    """Return diagnostic information for the current compliance context."""

    ctx = get_compliance_context()
    if ctx is None:
        return {
            "status": "inactive",
            "message": "No compliance context set - outside of @streamlined_node",
            "has_validator": False,
            "has_source_agent": False,
            "recommendations": [
                "Ensure state.copy() is called within a @streamlined_node decorated function",
                "Check that enable_compliance=True in workflow creation",
                "Verify node decorator has validator set",
            ],
        }

    validator = ctx.get("validator")
    source_agent = ctx.get("source_agent")
    status = "active" if validator and source_agent else "partial"
    message = (
        "Compliance context is active"
        if validator and source_agent
        else "Compliance context incomplete"
    )

    recommendations: list[str] = []
    if status != "active":
        recommendations = [
            "Check that workflow was created with enable_compliance=True",
            "Verify node decorator properly received validator",
        ]

    return {
        "status": status,
        "message": message,
        "has_validator": validator is not None,
        "has_source_agent": source_agent is not None,
        "context_keys": list(ctx.keys()),
        "validator_type": type(validator).__name__ if validator else None,
        "recommendations": recommendations,
    }
