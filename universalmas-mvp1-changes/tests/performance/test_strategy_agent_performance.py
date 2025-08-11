import asyncio
import time
from unittest.mock import patch

import pytest

from universal_framework.agents.strategy_generator import (
    StrategyGenerationError,
    StrategyGeneratorAgent,
)
from universal_framework.contracts.state import EmailRequirements
from universal_framework.llm.providers import LLMConfig


class TestStrategyGeneratorPerformance:
    @pytest.fixture
    def fast_llm_config(self):
        return LLMConfig(openai_api_key="sk-test", model_name="gpt-3.5-turbo")

    @pytest.fixture
    def sample_requirements(self):
        return EmailRequirements(
            purpose="Performance test communication",
            email_type="announcement",
            audience=["test_audience"],
            tone="professional",
            key_messages=["test message"],
            completeness_score=1.0,
        )

    @pytest.mark.asyncio
    async def test_enterprise_performance_compliance(
        self, fast_llm_config, sample_requirements
    ):
        agent = StrategyGeneratorAgent(fast_llm_config)
        with patch.object(agent.llm, "ainvoke") as mock_llm:
            mock_llm.return_value.content = "{}"
            start = time.perf_counter()
            await agent.generate_strategy(sample_requirements)
            duration = time.perf_counter() - start
            assert duration < 0.5
            assert agent.max_generation_time_seconds <= 0.4

    @pytest.mark.asyncio
    async def test_fallback_performance(self, fast_llm_config, sample_requirements):
        agent = StrategyGeneratorAgent(fast_llm_config)
        start = time.perf_counter()
        await agent._fallback_strategy_generation(sample_requirements)
        duration = time.perf_counter() - start
        assert duration < 0.1

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self, fast_llm_config, sample_requirements):
        agent = StrategyGeneratorAgent(fast_llm_config)

        async def slow(*args, **kwargs):
            await asyncio.sleep(1.0)
            return "delayed"

        with (
            patch.object(agent.llm, "ainvoke", side_effect=slow),
            pytest.raises(StrategyGenerationError),
        ):
            await agent.generate_strategy(sample_requirements)

    @pytest.mark.asyncio
    async def test_concurrent_performance(self, fast_llm_config, sample_requirements):
        agent = StrategyGeneratorAgent(fast_llm_config)
        with patch.object(agent.llm, "ainvoke") as mock_llm:
            mock_llm.return_value.content = "{}"
            tasks = [agent.generate_strategy(sample_requirements) for _ in range(5)]
            start = time.perf_counter()
            await asyncio.gather(*tasks)
            duration = time.perf_counter() - start
            assert duration / len(tasks) < 0.5
