from __future__ import annotations

import pytest

from universal_framework.contracts.messages import (
    create_agent_message,
)
from universal_framework.contracts.state import (
    EmailRequirements,
    UniversalWorkflowState,
    WorkflowPhase,
)
from universal_framework.workflow import (
    batch_requirements_collector,
    strategy_generator,
)


@pytest.mark.asyncio
async def test_batch_requirements_collector() -> None:
    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="t" * 10,
        workflow_phase=WorkflowPhase.BATCH_DISCOVERY,
    )
    msg = create_agent_message(
        from_agent="user",
        to_agent="batch_requirements_collector",
        content="collect",
        phase=WorkflowPhase.BATCH_DISCOVERY,
        data={"user_input": "Audience executives formal update"},
    )
    state = state.copy(update={"messages": [msg]})

    new_state = await batch_requirements_collector(state)
    assert new_state.context_data["last_active_agent"] == "batch_requirements_collector"
    assert "collected_requirements" in new_state.context_data
    assert "requirements_extraction" in new_state.context_data
    assert new_state.messages[-1].metadata["to_agent"] == "email_workflow_orchestrator"
    # Test enhanced component tracking
    assert "batch_requirements_collector" in new_state.component_status


@pytest.mark.asyncio
async def test_strategy_generation_success(mock_openai_provider, monkeypatch) -> None:
    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.OpenAIProvider",
        lambda: mock_openai_provider,
    )

    requirements = EmailRequirements(
        purpose="New policy rollout for Q3",
        email_type="announcement",
        audience=["team"],
        tone="professional",
        key_messages=["Policy effective date"],
        completeness_score=1.0,
    )

    state = UniversalWorkflowState(
        session_id="s",
        user_id="u",
        auth_token="t" * 10,
        workflow_phase=WorkflowPhase.STRATEGY_ANALYSIS,
        email_requirements=requirements,
    )

    new_state = await strategy_generator(state)
    assert new_state.email_strategy is not None
    assert new_state.conflict_analysis is not None
    assert new_state.email_strategy.overall_approach != ""
    assert new_state.component_status["strategy_generator"] == "completed"
    assert "strategy_generator" in new_state.component_outputs


@pytest.mark.asyncio
async def test_strategy_generation_with_conflicts(
    mock_openai_provider, monkeypatch
) -> None:
    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.OpenAIProvider",
        lambda: mock_openai_provider,
    )

    requirements = EmailRequirements(
        purpose="Urgent budget approval",
        email_type="request",
        audience=["executives"],
        tone="casual",
        key_messages=["Approve budget"],
        completeness_score=1.0,
    )

    state = UniversalWorkflowState(
        session_id="conflict",
        user_id="u",
        auth_token="t" * 10,
        workflow_phase=WorkflowPhase.STRATEGY_ANALYSIS,
        email_requirements=requirements,
        context_data={
            "user_preferences": {
                "organizational_tone": "formal",
                "preferred_length": "brief",
            }
        },
    )

    result_state = await strategy_generator(state)
    assert result_state.conflict_analysis is not None
    assert result_state.conflict_analysis.has_conflicts
    assert any(c["type"] == "tone" for c in result_state.conflict_analysis.conflicts)


@pytest.mark.asyncio
async def test_strategy_generation_llm_failure(monkeypatch) -> None:
    class FailingProvider:
        def create_agent_llm(self):
            class FailingLLM:
                async def ainvoke(self, prompt):
                    raise Exception("LLM timeout")

            return FailingLLM()

    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.OpenAIProvider",
        lambda: FailingProvider(),
    )

    requirements = EmailRequirements(
        purpose="Team update",
        email_type="update",
        audience=["team"],
        tone="professional",
        key_messages=["K1"],
        completeness_score=1.0,
    )

    state = UniversalWorkflowState(
        session_id="fallback_test",
        user_id="u",
        auth_token="t" * 10,
        workflow_phase=WorkflowPhase.STRATEGY_ANALYSIS,
        email_requirements=requirements,
    )

    result_state = await strategy_generator(state)
    assert result_state.email_strategy is not None
