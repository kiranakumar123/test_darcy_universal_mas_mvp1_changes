import pytest

from universal_framework.config.factory import LLMConfig
from universal_framework.nodes.strategy_confirmation_handler import (
    StrategyConfirmationHandler,
)


@pytest.mark.asyncio
async def test_node_instantiation_integration(monkeypatch) -> None:
    llm_config = LLMConfig(openai_api_key="k", model_name="gpt-4")
    monkeypatch.setattr(
        "universal_framework.nodes.business_logic.strategy_confirmation_node.get_llm_config",
        lambda: llm_config,
    )
    handler = StrategyConfirmationHandler()
    initialized = await handler._ensure_agent_initialized()
    assert initialized is True
    assert handler.agent is not None
    assert handler.agent.llm_config == llm_config
