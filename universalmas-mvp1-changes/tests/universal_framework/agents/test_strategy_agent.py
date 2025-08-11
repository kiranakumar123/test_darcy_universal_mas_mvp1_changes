import asyncio
import json
import os

import pytest

from universal_framework.agents.strategy_generator import StrategyGeneratorAgent
from universal_framework.contracts.state import EmailRequirements, EmailStrategy
from universal_framework.llm.providers import OpenAIProvider


class DummyExecutor:
    async def ainvoke(self, _input: dict[str, str]) -> dict[str, str]:
        strategy = {
            "overall_approach": "data-driven",
            "tone_strategy": "formal",
            "structure_strategy": ["intro"],
            "messaging_strategy": {"intro": "hi"},
            "personalization_strategy": {"name": "x"},
            "estimated_impact": "high",
            "confidence_score": 0.9,
        }
        return {"output": json.dumps(strategy)}


@pytest.mark.asyncio
async def test_strategy_agent_generate_strategy() -> None:
    os.environ["OPENAI_API_KEY"] = "sk-test"
    req = EmailRequirements(
        purpose="announce new product launch",
        audience=["executives"],
        tone="professional",
        key_messages=["launch"],
        completeness_score=1.0,
    )
    agent = StrategyGeneratorAgent(OpenAIProvider().config)
    result = await agent.generate_strategy(req)
    assert isinstance(result, EmailStrategy)
    assert result.tone_strategy == "formal"
    assert result.overall_approach == "data-driven"
    assert result.confidence_score == 0.9
    assert result.structure_strategy == ["intro"]


@pytest.mark.asyncio
async def test_strategy_agent_performance() -> None:
    os.environ["OPENAI_API_KEY"] = "sk-test"
    req = EmailRequirements(
        purpose="announce",
        audience=["executives"],
        tone="professional",
        key_messages=["x"],
        completeness_score=1.0,
    )
    agent = StrategyGeneratorAgent(OpenAIProvider().config)
    start = asyncio.get_event_loop().time()
    await agent.generate_strategy(req)
    duration = asyncio.get_event_loop().time() - start
    assert duration < 0.5
