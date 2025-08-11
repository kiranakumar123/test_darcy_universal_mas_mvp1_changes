"""
Tests for StrategyGeneratorNode workflow integration.
"""

from unittest.mock import AsyncMock, patch

import pytest

from universal_framework.contracts.state import (
    EmailRequirements,
    EmailStrategy,
    UniversalWorkflowState,
    WorkflowPhase,
)
from universal_framework.nodes.strategy_generator_node import (
    StrategyGeneratorNode,
    create_strategy_generator_node,
)


class TestStrategyGeneratorNode:
    """Test suite for StrategyGeneratorNode."""

    @pytest.fixture
    def mock_state_with_requirements(self):
        return UniversalWorkflowState(
            session_id="test_session",
            user_id="test_user",
            auth_token="token123456",
            workflow_phase=WorkflowPhase.STRATEGY_ANALYSIS,
            email_requirements=EmailRequirements(
                purpose="Test email purpose",
                email_type="announcement",
                audience=["Test audience"],
                tone="professional",
                key_messages=["Test information"],
                completeness_score=1.0,
            ),
            context_data={},
        )

    @pytest.fixture
    def mock_state_no_requirements(self):
        return UniversalWorkflowState(
            session_id="test_session",
            user_id="test_user",
            auth_token="token123456",
            workflow_phase=WorkflowPhase.STRATEGY_ANALYSIS,
            email_requirements=None,
            context_data={},
        )

    @pytest.fixture
    def strategy_node(self):
        node = StrategyGeneratorNode()
        node.agent = AsyncMock()
        return node

    @pytest.mark.asyncio
    async def test_execute_success(self, strategy_node, mock_state_with_requirements):
        mock_strategy = EmailStrategy(
            overall_approach="Test approach",
            tone_strategy="Professional",
            structure_strategy=[],
            messaging_strategy={},
            personalization_strategy={},
            estimated_impact="high",
            confidence_score=0.9,
            target_audience="Test audience",
            tone="Professional",
            approach="Test approach",
            key_messages=["Message 1"],
            timing_considerations="Immediate",
            success_metrics="High engagement",
        )
        strategy_node.agent.generate_strategy.return_value = mock_strategy
        result_state = await strategy_node.execute(mock_state_with_requirements)
        assert result_state.email_strategy == mock_strategy
        assert result_state.workflow_phase == WorkflowPhase.STRATEGY_CONFIRMATION
        assert result_state.current_node == "strategy_confirmation_handler"
        assert "strategy_generation" in result_state.context_data
        assert (
            result_state.context_data["strategy_generation"]["agent_used"]
            == "StrategyGeneratorAgent"
        )

    @pytest.mark.asyncio
    async def test_execute_no_requirements(
        self, strategy_node, mock_state_no_requirements
    ):
        result_state = await strategy_node.execute(mock_state_no_requirements)
        assert result_state.current_node == "requirements_collector"
        assert "requirements needed" in result_state.error_message.lower()
        strategy_node.agent.generate_strategy.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_agent_failure_with_fallback(
        self, strategy_node, mock_state_with_requirements
    ):
        strategy_node.agent.generate_strategy.side_effect = Exception("LLM API failed")
        with patch(
            "universal_framework.workflow.simulations.simulate_strategy_generation"
        ) as mock_sim:
            mock_fallback_strategy = EmailStrategy(
                overall_approach="Fallback approach",
                tone_strategy="Professional",
                structure_strategy=[],
                messaging_strategy={},
                personalization_strategy={},
                estimated_impact="medium",
                confidence_score=0.5,
                target_audience="Test audience",
                tone="Professional",
                approach="Fallback approach",
                key_messages=["Fallback message"],
                timing_considerations="Standard",
                success_metrics="Standard metrics",
            )
            mock_sim.return_value = mock_fallback_strategy
            result_state = await strategy_node.execute(mock_state_with_requirements)
            assert result_state.email_strategy == mock_fallback_strategy
            assert "failed, using fallback" in result_state.error_message
            assert (
                result_state.context_data["strategy_generation"]["agent_used"]
                == "simulation_fallback"
            )
            assert "error" in result_state.context_data["strategy_generation"]

    def test_create_strategy_generator_node_factory(self):
        node = create_strategy_generator_node()
        assert isinstance(node, StrategyGeneratorNode)
        assert hasattr(node, "agent")
        assert hasattr(node, "execute")
