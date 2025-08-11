import pytest

from universal_framework.agents import StrategyConfirmationAgent
from universal_framework.config.factory import LLMConfig


def test_constructor_with_llm_config() -> None:
    llm_config = LLMConfig(
        openai_api_key="sk-test",
        model_name="gpt-4",
        temperature=0.7,
        max_tokens=150,
    )
    agent = StrategyConfirmationAgent(llm_config)
    assert agent.llm_config == llm_config
    assert isinstance(agent, StrategyConfirmationAgent)


def test_constructor_with_none() -> None:
    agent = StrategyConfirmationAgent(None)
    assert agent.llm_config is None
    assert isinstance(agent, StrategyConfirmationAgent)


def test_constructor_default_parameter() -> None:
    agent = StrategyConfirmationAgent()
    assert agent.llm_config is None
    assert isinstance(agent, StrategyConfirmationAgent)


def test_constructor_invalid_parameter_type() -> None:
    with pytest.raises(TypeError):
        StrategyConfirmationAgent("bad")
    with pytest.raises(TypeError):
        StrategyConfirmationAgent(123)
