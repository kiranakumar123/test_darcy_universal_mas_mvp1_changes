"""Tests for email workflow orchestrator."""

from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.utils.session_logging import SessionFlowLogger
from universal_framework.workflow.orchestrator import (
    create_email_workflow_orchestrator,
)


@pytest.mark.asyncio
async def test_orchestrator_creation() -> None:
    """Test orchestrator can be created."""
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )
    assert orchestrator is not None


@pytest.mark.asyncio
async def test_initialization_routing() -> None:
    """Test orchestrator routes from initialization to requirements collector."""
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="test_session",
        user_id="test_user",
        auth_token="test_token_1234567890",
        workflow_phase=WorkflowPhase.INITIALIZATION,
    ).copy(
        update={"messages": [HumanMessage(content="Create an email for executives")]}
    )

    result_state = await orchestrator(state)

    routing_info = result_state.context_data.get("workflow_orchestration", {})
    assert routing_info.get("next_agent") == "batch_requirements_collector"
    assert "email_workflow_orchestrator" in [
        msg.metadata.get("from_agent")
        for msg in result_state.messages
        if hasattr(msg, "metadata")
    ]


@pytest.mark.asyncio
async def test_discovery_completion_routing() -> None:
    """Test orchestrator routes from discovery to strategy when complete."""
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="test_session",
        user_id="test_user",
        auth_token="test_token_1234567890",
        workflow_phase=WorkflowPhase.BATCH_DISCOVERY,
        phase_completion={"discovery": 0.9},
        context_data={
            "collected_requirements": {
                "audience": "executives",
                "tone": "professional",
            },
            "missing_requirements": [],
        },
    )

    result_state = await orchestrator(state)

    routing_info = result_state.context_data.get("workflow_orchestration", {})
    assert routing_info.get("next_agent") == "strategy_generator"


@pytest.mark.asyncio
async def test_incomplete_discovery_routing() -> None:
    """Test orchestrator keeps in discovery when incomplete."""
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="test_session",
        user_id="test_user",
        auth_token="test_token_1234567890",
        workflow_phase=WorkflowPhase.BATCH_DISCOVERY,
        phase_completion={"discovery": 0.4},
        context_data={"missing_requirements": ["audience", "tone"]},
    )

    result_state = await orchestrator(state)

    routing_info = result_state.context_data.get("workflow_orchestration", {})
    assert routing_info.get("next_agent") == "batch_requirements_collector"


@pytest.mark.asyncio
async def test_strategy_confirmation_approved() -> None:
    """Test orchestrator routes to email generator when strategy approved."""
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="test_session",
        user_id="test_user",
        auth_token="test_token_1234567890",
        workflow_phase=WorkflowPhase.STRATEGY_CONFIRMATION,
        context_data={
            "strategy_approved": True,
            "approved_strategy": {"approach": "formal"},
        },
    )

    result_state = await orchestrator(state)

    routing_info = result_state.context_data.get("workflow_orchestration", {})
    assert routing_info.get("next_agent") == "enhanced_email_generator"


@pytest.mark.asyncio
async def test_strategy_confirmation_rejected() -> None:
    """Test orchestrator routes back to strategy generator when rejected."""
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="test_session",
        user_id="test_user",
        auth_token="test_token_1234567890",
        workflow_phase=WorkflowPhase.STRATEGY_CONFIRMATION,
        context_data={
            "strategy_approved": False,
            "user_feedback": "Too formal",
        },
    )

    result_state = await orchestrator(state)

    routing_info = result_state.context_data.get("workflow_orchestration", {})
    assert routing_info.get("next_agent") == "strategy_generator"


@pytest.mark.asyncio
async def test_generation_completion() -> None:
    """Test orchestrator ends workflow after generation."""
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="test_session",
        user_id="test_user",
        auth_token="test_token_1234567890",
        workflow_phase=WorkflowPhase.GENERATION,
        context_data={"generated_email": {"subject": "Test", "body": "Content"}},
    )

    result_state = await orchestrator(state)

    routing_info = result_state.context_data.get("workflow_orchestration", {})
    assert routing_info.get("next_agent") == "END"


@pytest.mark.asyncio
async def test_strategy_analysis_routing() -> None:
    """Strategy analysis routes to confirmation handler."""
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="test_session",
        user_id="test_user",
        auth_token="test_token_1234567890",
        workflow_phase=WorkflowPhase.STRATEGY_ANALYSIS,
        context_data={"generated_strategy": {"summary": "s"}},
    )

    result_state = await orchestrator(state)

    routing_info = result_state.context_data.get("workflow_orchestration", {})
    assert routing_info.get("next_agent") == "strategy_confirmation_handler"


@pytest.mark.asyncio
async def test_review_phase_routing() -> None:
    """Unimplemented phases default to END."""
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="test_session",
        user_id="test_user",
        auth_token="test_token_1234567890",
        workflow_phase=WorkflowPhase.REVIEW,
    )

    result_state = await orchestrator(state)

    routing_info = result_state.context_data.get("workflow_orchestration", {})
    assert routing_info.get("next_agent") == "END"


@pytest.mark.asyncio
async def test_phase_transition_logging_uses_named_parameters() -> None:
    """SessionFlowLogger logs only on actual phase transitions."""
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="test_session",
        user_id="test_user",
        auth_token="test_token_1234567890",
        workflow_phase=WorkflowPhase.INITIALIZATION,
    )

    with patch.object(SessionFlowLogger, "log_workflow_phase_transition") as mock_log:
        await orchestrator(state)
        mock_log.assert_not_called()

    next_state = state.transition_to_phase(WorkflowPhase.BATCH_DISCOVERY)
    with patch.object(SessionFlowLogger, "log_workflow_phase_transition") as mock_log:
        await orchestrator(next_state)
        mock_log.assert_called_with(
            "test_session",
            "test_user",
            from_phase="initialization",
            to_phase="batch_discovery",
        )


@pytest.mark.asyncio
async def test_actual_phase_transition_logging() -> None:
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="sessionA",
        user_id="userA",
        auth_token="tok1234567890",
        workflow_phase=WorkflowPhase.INITIALIZATION,
    )

    transitioned = state.transition_to_phase(WorkflowPhase.BATCH_DISCOVERY)

    # First call initializes tracking without logging
    await orchestrator(state)

    with patch.object(SessionFlowLogger, "log_workflow_phase_transition") as mock_log:
        await orchestrator(transitioned)
        mock_log.assert_called_once_with(
            "sessionA",
            "userA",
            from_phase="initialization",
            to_phase="batch_discovery",
        )


@pytest.mark.asyncio
async def test_no_logging_same_phase() -> None:
    orchestrator = create_email_workflow_orchestrator(
        [
            "batch_requirements_collector",
            "strategy_generator",
            "strategy_confirmation_handler",
            "enhanced_email_generator",
        ]
    )

    state = UniversalWorkflowState(
        session_id="sessionB",
        user_id="userB",
        auth_token="tok0987654321",
        workflow_phase=WorkflowPhase.INITIALIZATION,
    )

    with patch.object(SessionFlowLogger, "log_workflow_phase_transition") as mock_log:
        await orchestrator(state)
        mock_log.assert_not_called()

    same_phase_state = state.transition_to_phase(WorkflowPhase.INITIALIZATION)
    with patch.object(SessionFlowLogger, "log_workflow_phase_transition") as mock_log:
        await orchestrator(same_phase_state)
        mock_log.assert_not_called()
