import pytest
from langchain_core.messages import HumanMessage

from universal_framework.agents.requirements_agent import real_requirements_collector
from universal_framework.contracts.state import UniversalWorkflowState


@pytest.mark.asyncio
async def test_full_requirements_collection_workflow(test_openai_config):
    state = UniversalWorkflowState(
        session_id="integration_session",
        user_id="integration_user",
        auth_token="token12345",
        messages=[HumanMessage(content="Email stakeholders about the merger plan")],
    )
    result = await real_requirements_collector(state)
    assert result.context_data.get("collected_requirements") is not None
    assert result.audit_trail
