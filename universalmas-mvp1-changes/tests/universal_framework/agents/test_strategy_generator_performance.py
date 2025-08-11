"""Performance validation tests for StrategyGenerator."""

from __future__ import annotations

import asyncio
import os
import time

import psutil
import pytest

from universal_framework.agents.strategy_generator import StrategyGenerator
from universal_framework.contracts.state import (
    EmailRequirements,
    UniversalWorkflowState,
    WorkflowPhase,
)


@pytest.mark.performance
@pytest.mark.asyncio
async def test_strategy_generation_performance_constraint(
    mock_openai_provider, dummy_agent_executor, monkeypatch
) -> None:
    """Validate strategy generation meets <500ms enterprise requirement."""
    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.OpenAIProvider",
        lambda: mock_openai_provider,
    )
    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.StrategyGenerator._create_agent_executor",
        lambda self: dummy_agent_executor,
    )

    requirements = EmailRequirements(
        purpose="Quarterly update for all teams",
        email_type="announcement",
        audience=["team", "management"],
        tone="professional",
        key_messages=["Q3 results", "Q4 goals", "team changes"],
        completeness_score=1.0,
    )

    state = UniversalWorkflowState(
        session_id="perf_test",
        user_id="test_user",
        auth_token="t" * 10,
        workflow_phase=WorkflowPhase.STRATEGY_ANALYSIS,
        email_requirements=requirements,
    )

    generator = StrategyGenerator()

    start_time = time.perf_counter()
    result = await generator.execute(state)
    execution_time = time.perf_counter() - start_time

    assert (
        execution_time < 0.5
    ), f"Strategy generation took {execution_time:.3f}s, exceeds 500ms limit"
    assert result.email_strategy is not None

    metrics = result.context_data.get("performance_metrics", {})
    assert "total_execution_time" in metrics
    assert metrics["total_execution_time"] < 0.5


@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_strategy_generation_performance(
    mock_openai_provider, dummy_agent_executor, monkeypatch
) -> None:
    """Validate performance under concurrent load."""
    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.OpenAIProvider",
        lambda: mock_openai_provider,
    )
    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.StrategyGenerator._create_agent_executor",
        lambda self: dummy_agent_executor,
    )

    async def generate_strategy(session_id: str) -> float:
        requirements = EmailRequirements(
            purpose=f"Test purpose {session_id}",
            email_type="update",
            audience=["team"],
            tone="professional",
            key_messages=["test"],
            completeness_score=1.0,
        )

        state = UniversalWorkflowState(
            session_id=session_id,
            user_id="concurrent_test",
            auth_token="t" * 10,
            workflow_phase=WorkflowPhase.STRATEGY_ANALYSIS,
            email_requirements=requirements,
        )

        generator = StrategyGenerator()
        start_time = time.perf_counter()
        await generator.execute(state)
        return time.perf_counter() - start_time

    tasks = [generate_strategy(f"session_{i}") for i in range(10)]
    execution_times = await asyncio.gather(*tasks)

    for i, exec_time in enumerate(execution_times):
        assert exec_time < 0.5, f"Concurrent execution {i} took {exec_time:.3f}s"

    avg_time = sum(execution_times) / len(execution_times)
    assert avg_time < 0.3, f"Average concurrent execution time {avg_time:.3f}s too high"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_strategy_generation_memory_usage(
    mock_openai_provider, dummy_agent_executor, monkeypatch
) -> None:
    """Validate memory usage remains within bounds."""

    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.OpenAIProvider",
        lambda: mock_openai_provider,
    )
    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.StrategyGenerator._create_agent_executor",
        lambda self: dummy_agent_executor,
    )

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024

    for i in range(100):
        requirements = EmailRequirements(
            purpose=f"Memory test {i}",
            email_type="announcement",
            audience=["team"],
            tone="professional",
            key_messages=[f"message_{i}"],
            completeness_score=1.0,
        )

        state = UniversalWorkflowState(
            session_id=f"mem_test_{i}",
            user_id="memory_test",
            auth_token="t" * 10,
            workflow_phase=WorkflowPhase.STRATEGY_ANALYSIS,
            email_requirements=requirements,
        )

        generator = StrategyGenerator()
        await generator.execute(state)

    final_memory = process.memory_info().rss / 1024 / 1024
    memory_increase = final_memory - initial_memory

    assert memory_increase < 50, f"Memory usage increased by {memory_increase:.1f}MB"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_agent_executor_vs_direct_llm_baseline(
    mock_openai_provider, dummy_agent_executor, monkeypatch
) -> None:
    """Compare agent executor overhead with direct LLM invocation."""
    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.OpenAIProvider",
        lambda: mock_openai_provider,
    )
    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.StrategyGenerator._create_agent_executor",
        lambda self: dummy_agent_executor,
    )

    generator = StrategyGenerator()
    prompt = "performance baseline"

    llm = mock_openai_provider.create_agent_llm()
    start_llm = time.perf_counter()
    await llm.ainvoke(prompt)
    llm_time = time.perf_counter() - start_llm

    start_agent = time.perf_counter()
    await generator.agent_executor.ainvoke({"input": prompt})
    agent_time = time.perf_counter() - start_agent

    assert agent_time >= llm_time
    assert agent_time - llm_time < 0.05


@pytest.mark.performance
@pytest.mark.asyncio
async def test_agent_executor_cleanup_memory_leak(
    mock_openai_provider, dummy_agent_executor, monkeypatch
) -> None:
    """Ensure agent executor cleanup does not leak memory."""
    import gc

    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.OpenAIProvider",
        lambda: mock_openai_provider,
    )
    monkeypatch.setattr(
        "universal_framework.agents.strategy_generator.StrategyGenerator._create_agent_executor",
        lambda self: dummy_agent_executor,
    )

    process = psutil.Process(os.getpid())
    start_mem = process.memory_info().rss / 1024 / 1024

    for _ in range(20):
        gen = StrategyGenerator()
        await gen.agent_executor.ainvoke({"input": "x"})
        del gen
        gc.collect()

    end_mem = process.memory_info().rss / 1024 / 1024
    assert end_mem - start_mem < 5
