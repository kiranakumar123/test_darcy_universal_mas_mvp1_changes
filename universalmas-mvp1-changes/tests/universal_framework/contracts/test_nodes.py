import pytest

from universal_framework.contracts.nodes import (
    format_response_for_phase,
    streamlined_node,
)
from universal_framework.contracts.state import (
    BatchCollectionResponse,
    EmailDeliveryResponse,
    GenerationProgressResponse,
    StrategyPresentationResponse,
    UniversalWorkflowState,
    WorkflowPhase,
)


@pytest.mark.asyncio
async def test_streamlined_node_decorator():
    sample_session_state = UniversalWorkflowState(
        session_id="s", user_id="u", auth_token="t" * 10
    )

    @streamlined_node("init_to_discovery", WorkflowPhase.INITIALIZATION)
    async def advance(state: UniversalWorkflowState) -> UniversalWorkflowState:
        return state.copy(update={"workflow_phase": WorkflowPhase.BATCH_DISCOVERY})

    new_state = await advance(sample_session_state)
    assert new_state.workflow_phase == WorkflowPhase.BATCH_DISCOVERY
    assert "ui_response" in new_state.context_data


@pytest.mark.asyncio
async def test_phase_validation():
    sample_discovery_state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="t" * 10,
        workflow_phase=WorkflowPhase.BATCH_DISCOVERY,
    )

    @streamlined_node("invalid_phase", WorkflowPhase.GENERATION)
    async def dummy(state: UniversalWorkflowState) -> UniversalWorkflowState:
        return state

    with pytest.raises(ValueError):
        await dummy(sample_discovery_state)


@pytest.mark.asyncio
async def test_error_routing():
    sample_session_state = UniversalWorkflowState(
        session_id="s", user_id="u", auth_token="t" * 10
    )

    @streamlined_node("error_node", WorkflowPhase.INITIALIZATION)
    async def boom(state: UniversalWorkflowState) -> UniversalWorkflowState:
        raise RuntimeError("boom")

    result = await boom(sample_session_state)
    assert result.error_info is not None
    assert result.error_info["node"] == "error_node"


@pytest.mark.asyncio
async def test_ui_response_formatting():
    for phase, expected in [
        (WorkflowPhase.BATCH_DISCOVERY, BatchCollectionResponse),
        (WorkflowPhase.STRATEGY_CONFIRMATION, StrategyPresentationResponse),
        (WorkflowPhase.GENERATION, GenerationProgressResponse),
        (WorkflowPhase.DELIVERY, EmailDeliveryResponse),
    ]:
        state = UniversalWorkflowState(
            session_id="s",
            user_id="u",
            auth_token="t" * 10,
            workflow_phase=phase,
        )
        resp = await format_response_for_phase(state, "default", "test")
        assert isinstance(resp, expected)


@pytest.mark.asyncio
async def test_streamlined_node_complete_workflow():
    sample_session_state = UniversalWorkflowState(
        session_id="s", user_id="u", auth_token="t" * 10
    )

    @streamlined_node("first", WorkflowPhase.INITIALIZATION)
    async def first(state: UniversalWorkflowState) -> UniversalWorkflowState:
        return state.copy(update={"workflow_phase": WorkflowPhase.BATCH_DISCOVERY})

    @streamlined_node("second", WorkflowPhase.BATCH_DISCOVERY)
    async def second(state: UniversalWorkflowState) -> UniversalWorkflowState:
        return state.copy(update={"workflow_phase": WorkflowPhase.STRATEGY_ANALYSIS})

    state = await first(sample_session_state)
    state = await second(state)
    assert state.workflow_phase == WorkflowPhase.STRATEGY_ANALYSIS


@pytest.mark.asyncio
async def test_reflection_validation_and_error_helpers():
    original = UniversalWorkflowState(session_id="a", user_id="b", auth_token="t" * 10)
    updated = original.copy(update={"workflow_phase": WorkflowPhase.BATCH_DISCOVERY})

    from universal_framework.contracts.nodes import (
        apply_streamlined_corrections,
        route_streamlined_error,
        validate_streamlined_logic,
    )

    result = await validate_streamlined_logic("node", original, updated)
    assert result["is_valid"]

    corrected = await apply_streamlined_corrections(updated, result)
    assert corrected.workflow_phase == WorkflowPhase.BATCH_DISCOVERY

    error_state = route_streamlined_error(updated, "node", "oops", "retry")
    assert error_state.error_info is not None


@pytest.mark.asyncio
async def test_reflection_correction(monkeypatch):
    calls: dict[str, bool] = {}

    async def fake_validate(name, old, new):
        calls["validate"] = True
        return {"is_valid": False}

    async def fake_apply(state, result):
        calls["apply"] = True
        return state

    monkeypatch.setattr(
        "universal_framework.contracts.nodes.validate_streamlined_logic", fake_validate
    )
    monkeypatch.setattr(
        "universal_framework.contracts.nodes.apply_streamlined_corrections", fake_apply
    )

    state = UniversalWorkflowState(session_id="s", user_id="u", auth_token="t" * 10)

    @streamlined_node(
        "batch_requirements_collector",
        WorkflowPhase.INITIALIZATION,
    )
    async def collector(s: UniversalWorkflowState) -> UniversalWorkflowState:
        return s.copy(update={"workflow_phase": WorkflowPhase.BATCH_DISCOVERY})

    await collector(state)
    assert calls == {"validate": True, "apply": True}


@pytest.mark.asyncio
async def test_checkpoint_created_and_completed() -> None:
    state = UniversalWorkflowState(session_id="s", user_id="u", auth_token="t" * 10)

    @streamlined_node("test_agent", WorkflowPhase.INITIALIZATION)
    async def agent(s: UniversalWorkflowState) -> UniversalWorkflowState:
        return s.copy(update={"workflow_phase": WorkflowPhase.BATCH_DISCOVERY})

    result = await agent(state)
    assert len(result.conversation_checkpoints) == 1
    cp = result.conversation_checkpoints[0]
    assert cp["metadata"]["status"] == "completed"
    assert "start_time" in cp["metadata"]
    assert "completion_time" in cp["metadata"]


@pytest.mark.asyncio
async def test_checkpoint_failure_status() -> None:
    state = UniversalWorkflowState(session_id="s", user_id="u", auth_token="t" * 10)

    @streamlined_node("failing_agent", WorkflowPhase.INITIALIZATION)
    async def bad_agent(s: UniversalWorkflowState) -> UniversalWorkflowState:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await bad_agent(state)

    assert len(state.conversation_checkpoints) == 1
    cp = state.conversation_checkpoints[0]
    assert cp["metadata"]["status"] == "failed"
    assert "error" in cp["metadata"]
