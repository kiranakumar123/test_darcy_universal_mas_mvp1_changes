from unittest.mock import patch

import pytest

from universal_framework.agents.strategy_generator import (
    StrategyGenerationError,
    StrategyGeneratorAgent,
)
from universal_framework.contracts.state import EmailRequirements
from universal_framework.llm.providers import LLMConfig


class TestStrategyGeneratorExceptions:
    @pytest.fixture
    def llm_config(self):
        return LLMConfig(openai_api_key="sk-test", model_name="gpt-3.5-turbo")

    @pytest.fixture
    def sample_requirements(self):
        return EmailRequirements(
            purpose="Test",
            email_type="announcement",
            audience=["test"],
            tone="professional",
            key_messages=["test"],
            completeness_score=1.0,
        )

    def test_llm_initialization_specific_exceptions(self, llm_config):
        with patch(
            "universal_framework.agents.strategy_generator.ChatOpenAI"
        ) as mock_openai:
            mock_openai.side_effect = ConnectionError("API connection failed")
            with pytest.raises(StrategyGenerationError) as exc_info:
                StrategyGeneratorAgent(llm_config)
            assert "LLM initialization failed" in str(exc_info.value)
            assert exc_info.value.__cause__ is not None
            assert isinstance(exc_info.value.__cause__, ConnectionError)

    @pytest.mark.asyncio
    async def test_strategy_generation_timeout_exception(
        self, llm_config, sample_requirements
    ):
        agent = StrategyGeneratorAgent(llm_config)
        agent.llm.ainvoke.side_effect = TimeoutError()
        with pytest.raises(StrategyGenerationError):
            await agent.generate_strategy(sample_requirements)

    @pytest.mark.asyncio
    async def test_no_broad_exception_catching(self, llm_config, sample_requirements):
        agent = StrategyGeneratorAgent(llm_config)

        with patch.object(agent, "_generate_strategy_with_llm") as mock_generate:
            mock_generate.side_effect = RuntimeError("Unexpected runtime error")
            with pytest.raises((RuntimeError, StrategyGenerationError)):
                await agent.generate_strategy(sample_requirements)
