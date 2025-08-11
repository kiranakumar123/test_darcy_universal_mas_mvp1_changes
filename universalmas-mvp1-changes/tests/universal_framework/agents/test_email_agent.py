import asyncio
import json
import os
from unittest.mock import patch

import pytest

from universal_framework.agents.email_agent import EmailGeneratorAgent
from universal_framework.contracts.state import (
    EmailRequirements,
    EmailStrategy,
    GeneratedEmail,
)
from universal_framework.llm.providers import OpenAIProvider


class DummyExecutor:
    async def ainvoke(self, _input: dict[str, str]) -> dict[str, str]:
        email = {
            "subject": "Hello",
            "html_content": "<p>Hi</p>",
            "text_content": "Hi",
            "quality_score": 0.95,
            "template_used": "default",
            "personalization_applied": {"name": "x"},
            "brand_compliance_score": 0.9,
            "strategy_applied": "data-driven",
        }
        return {"output": json.dumps(email)}


@pytest.mark.asyncio
async def test_email_generator_agent() -> None:
    """Legacy HTML-only compatibility test (generate_content)."""

    class MockLLM:
        async def ainvoke(self, messages):
            return type("Resp", (), {"content": "<html>hi</html>"})()

    class MockProvider:
        def create_agent_llm(self):
            return MockLLM()

    agent = EmailGeneratorAgent(MockProvider())
    strategy = EmailStrategy(
        overall_approach="a",
        tone_strategy="b",
        structure_strategy=[],
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="",
        confidence_score=0.9,
        subject="S",
        content="C",
        target_audience="A",
        tone="professional",
        call_to_action="Do",
        is_confirmed=True,
    )

    html = await agent.generate_content(strategy, "standard", {})
    assert html.startswith("<html>")


@pytest.mark.asyncio
async def test_email_agent_generate_email() -> None:
    os.environ["OPENAI_API_KEY"] = "sk-test"
    strategy = EmailStrategy(
        overall_approach="data",
        tone_strategy="formal",
        structure_strategy=["intro"],
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="high",
        confidence_score=0.9,
    )
    req = EmailRequirements(
        purpose="announce",
        audience=["executives"],
        tone="professional",
        key_messages=["x"],
    )
    with (
        patch(
            "universal_framework.agents.email_agent.AgentExecutor",
            return_value=DummyExecutor(),
        ),
        patch("universal_framework.agents.email_agent.create_openai_functions_agent"),
    ):
        agent = EmailGeneratorAgent(OpenAIProvider())
        result = await agent.generate_email(strategy, req, {})
        assert isinstance(result, GeneratedEmail)
        assert result.subject == "Hello"
        assert result.strategy_applied == "data-driven"


@pytest.mark.asyncio
async def test_email_agent_performance() -> None:
    os.environ["OPENAI_API_KEY"] = "sk-test"
    strategy = EmailStrategy(
        overall_approach="data",
        tone_strategy="formal",
        structure_strategy=["intro"],
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="high",
        confidence_score=0.9,
    )
    req = EmailRequirements(
        purpose="announce",
        audience=["executives"],
        tone="professional",
        key_messages=["x"],
    )
    with (
        patch(
            "universal_framework.agents.email_agent.AgentExecutor",
            return_value=DummyExecutor(),
        ),
        patch("universal_framework.agents.email_agent.create_openai_functions_agent"),
    ):
        agent = EmailGeneratorAgent(OpenAIProvider())
        start = asyncio.get_event_loop().time()
        await agent.generate_email(strategy, req, {})
        duration = asyncio.get_event_loop().time() - start
        assert duration < 0.5


def test_template_selector_integration() -> None:
    os.environ["OPENAI_API_KEY"] = "sk-test"
    agent = EmailGeneratorAgent(OpenAIProvider())
    strategy = EmailStrategy(
        overall_approach="a",
        tone_strategy="b",
        structure_strategy=[],
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="",
        confidence_score=1.0,
        content="Policy compliance update",
    )
    template = agent.select_template(strategy)
    assert template in agent.template_selector.get_available_templates()
