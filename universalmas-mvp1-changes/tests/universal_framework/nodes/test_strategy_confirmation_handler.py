from __future__ import annotations

import time

import pytest
from langchain_core.messages import HumanMessage

from universal_framework.contracts.state import (
    EmailStrategy,
    UniversalWorkflowState,
    WorkflowPhase,
)
from universal_framework.nodes.strategy_confirmation_handler import (
    StrategyConfirmationHandler,
)


def _create_strategy() -> EmailStrategy:
    return EmailStrategy(
        overall_approach="professional update",
        tone_strategy="casual",
        structure_strategy=["intro", "body"],
        messaging_strategy={"intro": "hi"},
        personalization_strategy={"name": "User"},
        estimated_impact="high",
        confidence_score=0.9,
    )


@pytest.mark.asyncio
async def test_strategy_approval() -> None:
    handler = StrategyConfirmationHandler()
    state = UniversalWorkflowState(
        session_id="test-001",
        user_id="u",
        auth_token="t" * 10,
        email_strategy=_create_strategy(),
        messages=[HumanMessage(content="I approve this strategy")],
    )
    result = await handler.execute(state)
    assert result.strategy_approved is True
    assert result.workflow_phase == WorkflowPhase.GENERATION
    assert "strategy_approved_at" in result.context_data


@pytest.mark.asyncio
async def test_strategy_modification() -> None:
    handler = StrategyConfirmationHandler()
    state = UniversalWorkflowState(
        session_id="test-002",
        user_id="u",
        auth_token="t" * 10,
        email_strategy=_create_strategy().copy(update={"tone_strategy": "casual"}),
        messages=[HumanMessage(content="Make it more formal and gradual timeline")],
    )
    result = await handler.execute(state)
    assert result.email_strategy.tone_strategy == "formal"
    assert result.context_data.get("modification_count", 0) == 1
    assert "strategy_modifications" in result.context_data


@pytest.mark.asyncio
async def test_strategy_rejection() -> None:
    handler = StrategyConfirmationHandler()
    state = UniversalWorkflowState(
        session_id="test-003",
        user_id="u",
        auth_token="t" * 10,
        email_strategy=_create_strategy(),
        messages=[HumanMessage(content="I reject this completely")],
    )
    result = await handler.execute(state)
    assert result.strategy_approved is False
    assert result.workflow_phase == WorkflowPhase.STRATEGY_ANALYSIS
    assert result.email_strategy is None


@pytest.mark.asyncio
async def test_missing_strategy() -> None:
    handler = StrategyConfirmationHandler()
    state = UniversalWorkflowState(
        session_id="test-004",
        user_id="u",
        auth_token="t" * 10,
        messages=[HumanMessage(content="approve")],
    )
    result = await handler.execute(state)
    assert result.workflow_phase == WorkflowPhase.STRATEGY_ANALYSIS
    assert result.context_data.get("error") == "missing_strategy_for_confirmation"


@pytest.mark.asyncio
async def test_ambiguous_input() -> None:
    handler = StrategyConfirmationHandler()
    state = UniversalWorkflowState(
        session_id="test-005",
        user_id="u",
        auth_token="t" * 10,
        email_strategy=_create_strategy(),
        messages=[HumanMessage(content="I'm not sure about this")],
    )
    result = await handler.execute(state)
    assert any("clarify" in m.content.lower() for m in result.messages)


@pytest.mark.asyncio
async def test_invalid_modifications() -> None:
    handler = StrategyConfirmationHandler()
    state = UniversalWorkflowState(
        session_id="test-006",
        user_id="u",
        auth_token="t" * 10,
        email_strategy=_create_strategy().copy(
            update={"overall_approach": "immediate"}
        ),
        messages=[HumanMessage(content="make it more urgent")],
    )
    result = await handler.execute(state)
    assert any("already" in m.content.lower() for m in result.messages)


@pytest.mark.asyncio
async def test_execution_performance() -> None:
    handler = StrategyConfirmationHandler()
    state = UniversalWorkflowState(
        session_id="test-007",
        user_id="u",
        auth_token="t" * 10,
        email_strategy=_create_strategy(),
        messages=[HumanMessage(content="approve")],
    )
    start = time.time()
    result = await handler.execute(state)
    duration = time.time() - start
    assert duration < 0.5
    assert result is not None
