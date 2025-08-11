from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from universal_framework.contracts.state import UniversalWorkflowState
from universal_framework.workflow.builder import (
    create_streamlined_workflow,
    execute_workflow_step,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("use_real_agents", [True, False])
async def test_workflow_with_real_and_simulation_modes(use_real_agents):
    """Workflow executes a step regardless of agent mode."""
    workflow = create_streamlined_workflow(use_real_agents=use_real_agents)
    state = UniversalWorkflowState(
        session_id="s-real" if use_real_agents else "s-sim",
        user_id="u",
        auth_token="t" * 10,
    ).copy(update={"messages": [HumanMessage(content="req audience formal")]})
    result_state = await execute_workflow_step(workflow, state)
    assert result_state.messages
