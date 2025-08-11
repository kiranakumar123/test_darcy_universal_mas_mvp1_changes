import logging

import pytest
from langchain_core.messages import HumanMessage

from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.workflow import MessageHistoryMode
from universal_framework.workflow.builder import (
    create_enhanced_workflow,
    create_streamlined_workflow,
    execute_workflow_step,
    validate_workflow_state,
)


@pytest.mark.asyncio
async def test_workflow_compilation() -> None:
    workflow = create_streamlined_workflow()
    assert workflow is not None


@pytest.mark.asyncio
async def test_orchestrator_routing() -> None:
    workflow = create_streamlined_workflow()
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="t" * 10,
    ).copy(
        update={
            "context_data": {"workflow_orchestration": {"next_agent": "END"}},
            "messages": [HumanMessage(content="hello")],
        }
    )
    new_state = await execute_workflow_step(workflow, state)
    routing = new_state.context_data.get("workflow_orchestration", {})
    assert routing.get("next_agent") == "END"


@pytest.mark.asyncio
async def test_agent_coordination() -> None:
    workflow = create_streamlined_workflow()
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="t" * 10,
    ).copy(update={"messages": [HumanMessage(content="req audience formal")]})

    # Step 1: orchestrator to requirements collector
    state = await execute_workflow_step(workflow, state)
    assert (
        state.context_data["workflow_orchestration"]["next_agent"]
        == "batch_requirements_collector"
    )

    # Step 2: run requirements collector
    state = await execute_workflow_step(workflow, state)
    assert state.context_data.get("last_active_agent") == "batch_requirements_collector"


@pytest.mark.asyncio
async def test_parallel_processing() -> None:
    workflow = create_streamlined_workflow(enable_parallel=True)
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="t" * 10,
        workflow_phase=WorkflowPhase.GENERATION,
        context_data={"approved_strategy": {"foo": "bar"}},
    )
    state = await execute_workflow_step(workflow, state)
    assert (
        "quality_validation" in state.context_data
        or state.workflow_phase == WorkflowPhase.DELIVERY
    )


@pytest.mark.asyncio
async def test_error_handling() -> None:
    workflow = create_streamlined_workflow()
    bad_state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="t" * 10,
    ).copy(
        update={"context_data": {"workflow_orchestration": {"next_agent": "invalid"}}}
    )

    new_state = await execute_workflow_step(workflow, bad_state)
    assert new_state.context_data["workflow_orchestration"]["next_agent"] == "END"


def test_performance_monitoring(caplog) -> None:
    caplog.set_level(logging.INFO)
    create_streamlined_workflow(performance_config={"enable_metrics": True})
    assert any("Performance monitoring enabled" in r.message for r in caplog.records)

    result = validate_workflow_state(
        UniversalWorkflowState(session_id="s", user_id="u", auth_token="t" * 10)
    )
    assert result["valid"]


@pytest.mark.asyncio
async def test_workflow_builder_message_history_integration(
    sample_state_with_messages,
) -> None:
    """Verify message history filtering integrates with workflow builder."""
    workflow = create_streamlined_workflow(
        message_history_mode=MessageHistoryMode.LAST_MESSAGE
    )
    new_state = await execute_workflow_step(workflow, sample_state_with_messages)
    assert len(new_state.messages) == 2
    assert (
        new_state.messages[0].content == sample_state_with_messages.messages[-1].content
    )


@pytest.mark.asyncio
async def test_create_enhanced_workflow() -> None:
    workflow = create_enhanced_workflow()
    assert workflow is not None
