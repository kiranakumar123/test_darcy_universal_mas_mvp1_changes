import pytest

from universal_framework.compliance import UnauthorizedStateUpdateError
from universal_framework.contracts.state import UniversalWorkflowState
from universal_framework.workflow.builder import create_streamlined_workflow


@pytest.mark.asyncio
async def test_transparent_state_validation() -> None:
    workflow = create_streamlined_workflow(
        use_real_agents=False, enable_compliance=True
    )
    state = UniversalWorkflowState(session_id="s", user_id="u", auth_token="t" * 10)
    result = await workflow.ainvoke(state, config={"configurable": {"thread_id": "t"}})
    assert result.audit_trail


def test_manual_unauthorized_update() -> None:
    workflow = create_streamlined_workflow(
        use_real_agents=False, enable_compliance=True
    )
    validator = workflow._validator
    state = UniversalWorkflowState(session_id="s", user_id="u", auth_token="t" * 10)
    with pytest.raises(UnauthorizedStateUpdateError):
        state.copy(
            update={"session_id": "new"},
            source_agent="strategy_generator",
            event="bad_update",
            validator=validator,
        )
