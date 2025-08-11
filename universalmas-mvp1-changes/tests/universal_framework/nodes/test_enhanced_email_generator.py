import importlib

import pytest

from universal_framework.contracts.state import (
    EmailStrategy,
    UniversalWorkflowState,
    WorkflowPhase,
)
from universal_framework.nodes.enhanced_email_generator import (
    EnhancedEmailGenerator,
)


class MockAgent:
    async def generate_content(self, *args, **kwargs) -> str:
        return "<html><body>Mock</body></html>"


def test_node_agent_separation() -> None:
    generator = EnhancedEmailGenerator()
    assert not hasattr(generator, "llm_provider")


def test_template_selection_logic() -> None:
    generator = EnhancedEmailGenerator()
    policy_strategy = EmailStrategy(
        overall_approach="a",
        tone_strategy="t",
        structure_strategy=[],
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="",
        confidence_score=0.9,
        content="New compliance policy requirements",
        is_confirmed=True,
    )
    result = generator._select_template(policy_strategy)
    assert result == "policy_communication"
    assert generator.template_selector.validate_template(result)
    training_strategy = policy_strategy.model_copy(
        update={"content": "Upcoming training workshop"}
    )
    result = generator._select_template(training_strategy)
    assert result == "educational_content"
    assert generator.template_selector.validate_template(result)
    announcement_strategy = policy_strategy.model_copy(
        update={"content": "Important announcement"}
    )
    result = generator._select_template(announcement_strategy)
    assert result == "executive_announcement"
    assert generator.template_selector.validate_template(result)


@pytest.mark.asyncio
async def test_generate_email_delegation(monkeypatch) -> None:
    class MockAgent:
        async def generate_content(self, *args, **kwargs) -> str:
            return "<html><body>Generated</body></html>"

    module = importlib.import_module(
        "universal_framework.nodes.enhanced_email_generator"
    )
    monkeypatch.setattr(module, "EmailGeneratorAgent", MockAgent)

    strategy = EmailStrategy(
        overall_approach="formal",
        tone_strategy="professional",
        structure_strategy=[],
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="",
        confidence_score=0.9,
        subject="Policy Update",
        content="Details",
        target_audience="All",
        tone="professional",
        call_to_action="Read",
        is_confirmed=True,
    )

    generator = EnhancedEmailGenerator()
    generator.workflow_builder = type(
        "B",
        (),
        {"create_email_generator_agent": lambda self: MockAgent()},
    )()
    result = await generator.generate_email(strategy, {})
    assert result.html_content.lstrip().startswith("<")
    assert result.text_content


@pytest.mark.asyncio
async def test_execute_generates_email(monkeypatch) -> None:
    class MockAgent:
        async def generate_content(self, *args, **kwargs) -> str:
            return "<html><body>Gen</body></html>"

    module = importlib.import_module(
        "universal_framework.nodes.enhanced_email_generator"
    )
    monkeypatch.setattr(module, "EmailGeneratorAgent", MockAgent)

    strategy = EmailStrategy(
        overall_approach="formal",
        tone_strategy="professional",
        structure_strategy=[],
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="",
        confidence_score=0.9,
        subject="Greetings",
        content="Body",
        target_audience="All",
        tone="professional",
        call_to_action="Do",
        is_confirmed=True,
    )

    state = UniversalWorkflowState(
        session_id="s1",
        user_id="u",
        auth_token="t" * 10,
        workflow_phase=WorkflowPhase.GENERATION,
        email_strategy=strategy,
    )

    generator = EnhancedEmailGenerator()
    generator.workflow_builder = type(
        "B",
        (),
        {"create_email_generator_agent": lambda self: MockAgent()},
    )()
    result_state = await generator.execute(state)

    assert result_state.workflow_phase == WorkflowPhase.REVIEW
    assert "generated_email" in result_state.generated_outputs
    assert result_state.component_status["enhanced_email_generator"] == "completed"


@pytest.mark.asyncio
async def test_execute_requires_confirmed_strategy() -> None:
    strategy = EmailStrategy(
        overall_approach="formal",
        tone_strategy="professional",
        structure_strategy=[],
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="",
        confidence_score=0.9,
        subject="Greetings",
        content="Body",
        target_audience="All",
        tone="professional",
        call_to_action="Do",
        is_confirmed=False,
    )

    state = UniversalWorkflowState(
        session_id="s2",
        user_id="u",
        auth_token="t" * 10,
        workflow_phase=WorkflowPhase.GENERATION,
        email_strategy=strategy,
    )

    generator = EnhancedEmailGenerator()
    generator.workflow_builder = type(
        "B",
        (),
        {"create_email_generator_agent": lambda self: MockAgent()},
    )()
    result_state = await generator.execute(state)

    assert result_state.component_status["enhanced_email_generator"] == "failed"
    assert "error_message" in result_state.context_data
