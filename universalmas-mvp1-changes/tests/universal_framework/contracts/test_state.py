import pytest
from pydantic import ValidationError

from universal_framework.contracts.state import (
    BatchCollectionResponse,
    ConflictAnalysis,
    EmailDeliveryResponse,
    EmailRequirements,
    EmailStrategy,
    GeneratedEmail,
    GenerationProgressResponse,
    StrategyPresentationResponse,
    UniversalWorkflowState,
    ValidationResult,
    WorkflowPhase,
)


def test_batch_requirements_update():
    state = UniversalWorkflowState(
        session_id="test", user_id="user", auth_token="token123456"
    )
    requirements = EmailRequirements(
        purpose="Test email for team",
        audience=["team"],
        tone="professional",
        key_messages=["Message 1"],
        completeness_score=0.9,
    )
    updated_state = state.update_requirements(requirements)
    assert updated_state.workflow_phase == WorkflowPhase.STRATEGY_ANALYSIS
    assert updated_state.email_requirements == requirements


def test_requirements_incomplete_remain_discovery():
    state = UniversalWorkflowState(
        session_id="test", user_id="user", auth_token="token123456"
    )
    requirements = EmailRequirements(
        purpose="Incomplete email",
        audience=["team"],
        tone="professional",
        key_messages=["Message 1"],
        completeness_score=0.5,
    )
    updated_state = state.update_requirements(requirements)
    assert updated_state.workflow_phase == WorkflowPhase.BATCH_DISCOVERY


def test_strategy_conflict_routing():
    state = UniversalWorkflowState(
        session_id="test", user_id="user", auth_token="token123456"
    )
    strategy = EmailStrategy(
        overall_approach="enhanced",
        tone_strategy="professional",
        structure_strategy=["intro", "body", "close"],
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="positive",
        confidence_score=0.8,
    )
    conflicts = ConflictAnalysis(has_conflicts=True, confidence_score=0.9)
    updated_state = state.update_strategy(strategy, conflicts)
    assert updated_state.workflow_phase == WorkflowPhase.STRATEGY_CONFIRMATION
    assert updated_state.email_strategy == strategy


def test_strategy_no_conflict_routing():
    state = UniversalWorkflowState(
        session_id="test", user_id="user", auth_token="token123456"
    )
    strategy = EmailStrategy(
        overall_approach="enhanced",
        tone_strategy="professional",
        structure_strategy=["intro", "body", "close"],
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="positive",
        confidence_score=0.8,
    )
    conflicts = ConflictAnalysis(has_conflicts=False, confidence_score=0.9)
    updated_state = state.update_strategy(strategy, conflicts)
    assert updated_state.workflow_phase == WorkflowPhase.GENERATION


def test_approve_strategy_paths():
    state = UniversalWorkflowState(
        session_id="test", user_id="user", auth_token="token123456"
    )
    approved_state = state.approve_strategy(True)
    assert approved_state.workflow_phase == WorkflowPhase.GENERATION
    rejected_state = state.approve_strategy(False)
    assert rejected_state.workflow_phase == WorkflowPhase.STRATEGY_ANALYSIS


def test_state_immutable():
    state = UniversalWorkflowState(
        session_id="test", user_id="user", auth_token="token123456"
    )
    with pytest.raises((TypeError, ValidationError)):
        state.user_id = "other"


def test_validation_error_on_invalid_fields():
    with pytest.raises(ValidationError):
        EmailRequirements(
            purpose="short",
            audience=[],
            tone="professional",
            key_messages=[],
            completeness_score=1.1,
        )


def test_ui_response_dicts():
    batch = BatchCollectionResponse(
        message="msg",
        collection_progress={"purpose": "✓"},
        missing_requirements=[],
        completion_percentage=1.0,
        next_action="proceed_to_strategy",
    )
    assert batch.model_dump()["next_action"] == "proceed_to_strategy"

    strat = StrategyPresentationResponse(
        message="m",
        strategy_summary={},
        conflict_detected=False,
        user_options=["approve"],
        strategy_confidence=0.9,
    )
    assert strat.model_dump()["conflict_detected"] is False

    progress = GenerationProgressResponse(
        message="m",
        generation_status="planning",
        progress_percentage=0.0,
        estimated_completion="soon",
    )
    assert progress.model_dump()["generation_status"] == "planning"

    delivery = EmailDeliveryResponse(
        message="m",
        email_preview="test",
        quality_metrics={"score": 1.0},
        available_actions=["save"],
        export_options=["pdf"],
    )
    assert "email_preview" in delivery.model_dump()


def test_generated_email_valid():
    model = GeneratedEmail(
        subject="Welcome",
        html_content="<html>Hello World</html>",
        text_content="Hello World",
        quality_score=0.85,
        template_used="welcome_template",
        personalization_applied={"name": "John"},
        brand_compliance_score=0.95,
        strategy_applied="enthusiastic_onboarding",
    )
    assert model.quality_score == 0.85


def test_validation_result_valid():
    model = ValidationResult(
        is_approved=True,
        quality_scores={"clarity": 0.9},
        issues=[],
    )
    assert model.is_approved


def test_generated_email_invalid_score():
    with pytest.raises(ValueError):
        GeneratedEmail(
            subject="Bad",
            html_content="short",
            text_content="short",
            quality_score=1.2,
            template_used="t",
            personalization_applied={},
            brand_compliance_score=1.1,
            strategy_applied="s",
        )


def test_conversation_checkpoints_default() -> None:
    """State initializes checkpoints as an empty list."""
    state = UniversalWorkflowState(
        session_id="test",
        user_id="user",
        auth_token="token123456",
    )
    assert state.conversation_checkpoints == []
    assert isinstance(state.conversation_checkpoints, list)


def test_conversation_checkpoints_initialization() -> None:
    """State accepts predefined checkpoint list."""
    checkpoints = [
        {
            "node": "test_node",
            "timestamp": "2024-07-19T10:00:00Z",
            "phase": WorkflowPhase.INITIALIZATION,
            "completion": {"init": 1.0},
        }
    ]
    state = UniversalWorkflowState(
        session_id="test",
        user_id="user",
        auth_token="token123456",
        conversation_checkpoints=checkpoints,
    )
    assert len(state.conversation_checkpoints) == 1
    assert state.conversation_checkpoints[0]["node"] == "test_node"


def test_conversation_checkpoints_mutability() -> None:
    """Checkpoints maintain independence across instances."""
    state1 = UniversalWorkflowState(
        session_id="s1",
        user_id="user",
        auth_token="token123456",
    )
    state2 = UniversalWorkflowState(
        session_id="s2",
        user_id="user",
        auth_token="token123456",
    )

    updated_state1 = state1.model_copy(
        update={
            "conversation_checkpoints": state1.conversation_checkpoints
            + [{"node": "n", "timestamp": "now"}]
        }
    )

    assert len(updated_state1.conversation_checkpoints) == 1
    assert len(state1.conversation_checkpoints) == 0
    assert len(state2.conversation_checkpoints) == 0


def test_conversation_checkpoints_immutability() -> None:
    """Ensure direct mutation is prevented for frozen model."""
    state = UniversalWorkflowState(
        session_id="test",
        user_id="user",
        auth_token="token123456",
    )
    with pytest.raises(ValidationError):
        state.conversation_checkpoints = []


def test_conversation_checkpoints_serialization() -> None:
    """State with checkpoints serializes and deserializes correctly."""
    import json

    checkpoints = [
        {"node": "test", "phase": "init", "timestamp": "2024-07-19T10:00:00Z"}
    ]
    state = UniversalWorkflowState(
        session_id="test",
        user_id="user",
        auth_token="token123456",
        conversation_checkpoints=checkpoints,
    )
    state_dict = state.model_dump()
    json_str = json.dumps(state_dict, default=str)
    loaded_dict = json.loads(json_str)
    assert loaded_dict["conversation_checkpoints"] == checkpoints


@pytest.mark.asyncio
async def test_checkpoint_workflow_integration() -> None:
    """Ensure checkpoints created during workflow execution."""
    from langchain_core.messages import HumanMessage

    from universal_framework.workflow import create_streamlined_workflow

    workflow = create_streamlined_workflow()

    initial_state = UniversalWorkflowState(
        session_id="checkpoint_test",
        user_id="test_user",
        auth_token="test_token_1234567890",
        messages=[HumanMessage(content="Test checkpoint creation")],
    )

    config = {"configurable": {"thread_id": "checkpoint_test"}}
    result_state = await workflow.ainvoke(initial_state, config=config)

    assert len(result_state.conversation_checkpoints) > 0
    latest_checkpoint = result_state.conversation_checkpoints[-1]
    assert "node" in latest_checkpoint
    assert "timestamp" in latest_checkpoint
    assert "phase" in latest_checkpoint
    assert "completion" in latest_checkpoint
    assert "metadata" in latest_checkpoint


def test_checkpoint_structure_validation() -> None:
    """Validate checkpoint dictionary structure."""
    from datetime import datetime

    valid_checkpoint = {
        "node": "batch_requirements_collector",
        "timestamp": datetime.now().isoformat(),
        "phase": WorkflowPhase.BATCH_DISCOVERY.value,
        "completion": {"discovery": 0.6, "analysis": 0.0},
        "context": {"collected_requirements": {"audience": "executives"}},
        "metadata": {"execution_time": 1.2, "retry_count": 0},
    }

    state = UniversalWorkflowState(
        session_id="validation_test",
        user_id="test_user",
        auth_token="test_token_123",
        conversation_checkpoints=[valid_checkpoint],
    )

    assert len(state.conversation_checkpoints) == 1
    checkpoint = state.conversation_checkpoints[0]
    assert isinstance(checkpoint["node"], str)
    assert isinstance(checkpoint["timestamp"], str)
    assert isinstance(checkpoint["phase"], str)
    assert isinstance(checkpoint["completion"], dict)
    assert isinstance(checkpoint["metadata"], dict)


def test_state_new_fields_defaults() -> None:
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="token123456",
    )
    assert state.component_outputs == {}
    assert state.component_status == {}
    assert state.audit_trail == []


def test_error_recovery_fields_defaults() -> None:
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="token123456",
    )

    assert state.error_recovery_state == {}
    assert state.routing_history == []
    assert state.escalation_count == 0
    assert state.recovery_attempts == {}
    assert state.circuit_breaker_states == {}
    assert state.last_successful_checkpoint is None
    assert state.performance_warnings == []


def test_enterprise_observability_fields_defaults() -> None:
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="token123456",
    )
    assert state.enterprise_trace_metadata == {}
    assert state.langsmith_circuit_breaker_state == "CLOSED"
    assert state.tool_call_trace_ids == {}
    assert state.reasoning_trace_correlation == {}
    assert state.cost_trace_metadata == {}


def test_transition_to_phase_method() -> None:
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="token123456",
    )
    new_state = state.transition_to_phase(WorkflowPhase.BATCH_DISCOVERY)
    assert new_state.workflow_phase == WorkflowPhase.BATCH_DISCOVERY
    assert new_state.previous_phase == WorkflowPhase.INITIALIZATION
    assert new_state.phase_completion.get("batch_discovery") == 0.0

    assert new_state.has_phase_transition() is True
    ctx = new_state.get_transition_context()
    assert ctx["from_phase"] == "initialization"
    assert ctx["to_phase"] == "batch_discovery"


def test_phase_transition_tracking() -> None:
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="token123456",
    )
    same_phase_state = state.transition_to_phase(WorkflowPhase.INITIALIZATION)
    assert same_phase_state.has_phase_transition() is False
    assert same_phase_state.get_transition_context() == {}
