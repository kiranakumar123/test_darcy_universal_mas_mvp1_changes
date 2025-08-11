"""Test configuration and fixtures for Universal Framework."""

import json
import os
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from universal_framework.agents.requirements_agent import RequirementsCollectorAgent
from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.llm.providers import LLMConfig, OpenAIProvider


@pytest.fixture
def mock_openai_api_key():
    """Mock OpenAI API key for testing."""
    return "test-openai-key-12345"


@pytest.fixture
def test_llm_config(mock_openai_api_key):
    """Test LLM configuration."""
    return LLMConfig(
        openai_api_key=mock_openai_api_key,
        model_name="gpt-4",
        temperature=0.1,
        max_tokens=1000,
    )


@pytest.fixture
def mock_openai_provider(test_llm_config):
    """Mock OpenAI provider for testing."""
    provider = OpenAIProvider(test_llm_config)

    # Mock the LLM to avoid real API calls
    provider._llm = MagicMock()
    provider._llm.ainvoke = AsyncMock(return_value=MagicMock(content="Test response"))

    # Ensure compatibility with tool-based agent creation
    provider._llm.bind_tools = MagicMock(return_value=provider._llm)
    provider.create_agent_llm = MagicMock(return_value=provider._llm)

    return provider


@pytest.fixture
def dummy_agent_executor() -> Any:
    """Simple agent executor that returns basic strategy JSON."""

    async def _ainvoke(_: dict[str, Any]) -> dict[str, str]:
        return {
            "output": json.dumps(
                {
                    "approach": "auto",
                    "tone": "professional",
                    "structure": [],
                    "confidence": 0.9,
                }
            )
        }

    return SimpleNamespace(ainvoke=AsyncMock(side_effect=_ainvoke))


@pytest.fixture
def test_workflow_state():
    """Test workflow state for agent testing."""
    return UniversalWorkflowState(
        session_id="test_session_001",
        user_id="test_user",
        auth_token="test_token_123",
        workflow_phase=WorkflowPhase.INITIALIZATION,
        messages=[HumanMessage(content="Create a test email")],
        context_data={},
    )


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    env_vars = {
        "OPENAI_API_KEY": "test-key-123",
        "LANGSMITH_API_KEY": "test-langsmith-key",
        "LANGCHAIN_TRACING_V2": "false",  # Disable for tests
    }

    for key, value in env_vars.items():
        os.environ[key] = value

    yield env_vars

    # Cleanup
    for key in env_vars:
        os.environ.pop(key, None)


@pytest.fixture
async def real_requirements_agent(test_openai_config):
    """Real RequirementsCollectorAgent instance for integration tests."""
    provider = OpenAIProvider(test_openai_config)
    agent = RequirementsCollectorAgent(provider)
    sample_state = UniversalWorkflowState(
        session_id="init_session",
        user_id="init_user",
        auth_token="init_token" * 2,
    )
    agent.agent_executor = agent._create_agent(sample_state)
    return agent


@pytest.fixture
def test_openai_config():
    """Real OpenAI configuration for tests requiring API access."""
    api_key = os.environ.get("OPENAI_TEST_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_TEST_API_KEY not set - skipping real agent tests")
    return LLMConfig(openai_api_key=api_key, model_name="gpt-3.5-turbo")
