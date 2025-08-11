import json
import os
from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from universal_framework.agents.requirements_agent import (
    AgentExecutionStatus,
    RequirementsCollectorAgent,
)
from universal_framework.contracts.state import UniversalWorkflowState
from universal_framework.llm.providers import LLMConfig


class DummyExecutor:
    async def ainvoke(self, _input: dict[str, str]) -> dict[str, str]:
        req = {"audience": "executives", "tone": "formal", "purpose": "update"}
        return {"output": json.dumps(req)}


@pytest.mark.asyncio
async def test_requirements_collector_execute() -> None:
    os.environ["OPENAI_API_KEY"] = "sk-test"
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="t" * 10,
        messages=[HumanMessage(content="Please update executives formally")],
    )
    with patch.object(
        RequirementsCollectorAgent,
        "_create_agent",
        return_value=DummyExecutor(),
    ):
        agent = RequirementsCollectorAgent()
        result = await agent.execute(state)
        assert result["status"] == AgentExecutionStatus.COMPLETED.value
        assert result["requirements"]["audience"] == "executives"


@pytest.mark.asyncio
async def test_requirements_agent_no_input() -> None:
    os.environ["OPENAI_API_KEY"] = "sk-test"
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="t" * 10,
        messages=[],
    )
    agent = RequirementsCollectorAgent()
    with patch.object(
        RequirementsCollectorAgent,
        "_create_agent",
        return_value=DummyExecutor(),
    ):
        result = await agent.execute(state)
        assert result["status"] == AgentExecutionStatus.ERROR.value


def test_provider_injection() -> None:
    class MockProvider:
        def __init__(self) -> None:
            self.config = LLMConfig(
                openai_api_key="test-key", model_name="mock", temperature=0.0
            )

        def create_agent_llm(self) -> object:
            return object()

    provider = MockProvider()
    agent = RequirementsCollectorAgent(llm_provider=provider)
    assert agent.llm_provider is provider
