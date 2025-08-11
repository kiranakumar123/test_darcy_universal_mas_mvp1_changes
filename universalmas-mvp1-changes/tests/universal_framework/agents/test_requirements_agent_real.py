import pytest
from langchain_core.messages import HumanMessage

from universal_framework.agents.requirements_agent import (
    real_requirements_collector,
)
from universal_framework.contracts.state import UniversalWorkflowState


class TestRequirementsCollectorAgentReal:
    """Test RequirementsCollectorAgent with real execution."""

    @pytest.mark.asyncio
    async def test_create_agent_real_initialization(self, real_requirements_agent):
        assert real_requirements_agent.agent_executor is not None
        assert hasattr(real_requirements_agent, "llm_provider")

    @pytest.mark.asyncio
    async def test_execute_real_requirements_extraction(self, real_requirements_agent):
        state = UniversalWorkflowState(
            session_id="test_session",
            user_id="test_user",
            auth_token="token12345",
            messages=[
                HumanMessage(content="I need to email our board about Q4 results")
            ],
        )
        result = await real_requirements_agent.execute(state)
        assert result["status"] in {"completed", "fallback"}
        assert "requirements" in result or "fallback_requirements" in result


@pytest.mark.asyncio
async def test_real_requirements_collector_integration(test_openai_config):
    state = UniversalWorkflowState(
        session_id="workflow_session",
        user_id="workflow_user",
        auth_token="token12345",
        messages=[HumanMessage(content="Send a summary of our KPIs to execs")],
    )
    result_state = await real_requirements_collector(state)
    assert result_state.context_data.get("collected_requirements") is not None
    assert result_state.workflow_phase.value == "batch_discovery"
