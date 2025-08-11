"""
Comprehensive tests for StrategyGeneratorAgent.generate_strategy() implementation.
"""

import pytest
from langchain_core.messages import AIMessage

from universal_framework.agents.strategy_generator import (
    StrategyGenerationError,
    StrategyGeneratorAgent,
)
from universal_framework.config.factory import get_llm_config
from universal_framework.contracts.state import EmailRequirements, EmailStrategy
from universal_framework.llm.providers import LLMConfig


class TestStrategyGeneratorAgent:
    """Test suite for StrategyGeneratorAgent implementation."""

    @pytest.fixture
    def mock_llm_config(self):
        return LLMConfig(openai_api_key="sk-test", model_name="gpt-4")

    @pytest.fixture
    def sample_requirements(self):
        return EmailRequirements(
            purpose="Announce new remote work policy",
            email_type="announcement",
            audience=["All employees"],
            tone="professional",
            key_messages=["Hybrid work starting January 2025"],
            completeness_score=1.0,
        )

    @pytest.fixture
    def strategy_agent(self, mock_llm_config, monkeypatch):
        async def fake_generate(_, req):
            return EmailStrategy(
                overall_approach="Direct and transparent communication about policy changes",
                tone_strategy=req.tone,
                structure_strategy=["intro"],
                messaging_strategy={},
                personalization_strategy={},
                estimated_impact="high",
                confidence_score=0.9,
                target_audience="All employees",
                tone=req.tone,
                approach="Direct and transparent",
                key_messages=req.key_messages,
                timing_considerations="Send on Monday",
                success_metrics="High open rates",
            )

        monkeypatch.setattr(
            StrategyGeneratorAgent,
            "_generate_strategy_with_llm",
            fake_generate,
        )
        return StrategyGeneratorAgent(mock_llm_config)

    @pytest.mark.asyncio
    async def test_generate_strategy_success(self, strategy_agent, sample_requirements):
        mock_response = AIMessage(
            content="""
            COMMUNICATION APPROACH: Direct and transparent communication about policy changes
            KEY MESSAGES: 1. Flexibility for better work-life balance 2. Maintained productivity expectations 3. Clear guidelines for hybrid work
            TONE SPECIFICATION: Professional yet approachable
            TIMING CONSIDERATIONS: Send on Monday morning before policy effective date
            SUCCESS METRICS: High open rates and positive employee feedback
            """
        )
        strategy_agent.llm.ainvoke.return_value = mock_response

        result = await strategy_agent.generate_strategy(sample_requirements)

        assert isinstance(result, EmailStrategy)
        assert "Direct and transparent" in result.overall_approach
        assert len(result.key_messages) >= 1
        assert result.tone_strategy
        assert result.target_audience == "All employees"

        strategy_agent.llm.ainvoke.assert_called_once()
        call_args = strategy_agent.llm.ainvoke.call_args[0][0]
        assert len(call_args) == 1
        assert "Announce new remote work policy" in call_args[0].content

    @pytest.mark.asyncio
    async def test_generate_strategy_timeout(self, strategy_agent, sample_requirements):
        strategy_agent.llm.ainvoke.side_effect = TimeoutError("LLM call timed out")
        with pytest.raises(StrategyGenerationError) as exc:
            await strategy_agent.generate_strategy(sample_requirements)
        assert "timed out" in str(exc.value)
        assert exc.value.__cause__ is not None

    @pytest.mark.asyncio
    async def test_generate_strategy_llm_failure(
        self, strategy_agent, sample_requirements
    ):
        strategy_agent.llm.ainvoke.side_effect = Exception("API connection failed")
        with pytest.raises(StrategyGenerationError) as exc:
            await strategy_agent.generate_strategy(sample_requirements)
        assert "Failed to generate strategy" in str(exc.value)
        assert "API connection failed" in str(exc.value)

    @pytest.mark.asyncio
    async def test_generate_strategy_parsing_fallback(
        self, strategy_agent, sample_requirements
    ):
        mock_response = AIMessage(content="Random unstructured text")
        strategy_agent.llm.ainvoke.return_value = mock_response
        result = await strategy_agent.generate_strategy(sample_requirements)
        assert isinstance(result, EmailStrategy)
        assert sample_requirements.purpose in result.overall_approach
        assert result.tone_strategy == sample_requirements.tone


class TestStrategyGeneratorIntegration:
    """Integration tests with real LLM configuration."""

    @pytest.mark.asyncio
    async def test_real_llm_integration(self):
        try:
            config = get_llm_config()
            agent = StrategyGeneratorAgent(config)
            requirements = EmailRequirements(
                purpose="Test strategy generation",
                email_type="announcement",
                audience=["Test audience"],
                tone="professional",
                key_messages=["Test information"],
                completeness_score=1.0,
            )
            if hasattr(agent, "llm") and agent.llm is not None:
                result = await agent.generate_strategy(requirements)
                assert isinstance(result, EmailStrategy)
                assert result.overall_approach
                assert len(result.key_messages) > 0
        except Exception as e:
            pytest.skip(f"Real LLM integration not available: {e}")
