"""
Strategy Generator Node for Universal Multi-Agent Framework

LangGraph-aligned business logic node that generates email strategies using enterprise patterns.
Integrates with StrategyGenerationAgent while maintaining single responsibility.

Architecture:
- LangGraph node wrapper for StrategyGenerationAgent
- Single responsibility: Strategy generation business logic
- Defensive programming for state handling
- Enterprise observability and circuit breaker patterns
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any

from universal_framework.config.feature_flags import feature_flags

# Conditional LangSmith tracing following established patterns
try:
    if feature_flags.is_enabled("LANGSMITH_TRACING"):
        from langsmith import traceable

        _LANGSMITH_AVAILABLE = True
    else:

        def traceable(name: str = None, **kwargs):  # noqa: ARG001
            def decorator(func):
                return func

            return decorator

        _LANGSMITH_AVAILABLE = False
except ImportError:

    def traceable(name: str = None, **kwargs):  # noqa: ARG001
        def decorator(func):
            return func

        return decorator

    _LANGSMITH_AVAILABLE = False

from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.nodes.agents import StrategyGenerationAgent
from universal_framework.nodes.base import BaseNode
from universal_framework.observability import UniversalFrameworkLogger

# Initialize enterprise logger
logger = UniversalFrameworkLogger("strategy_generator_node")


class StrategyGeneratorNode(BaseNode):
    """
    LangGraph-aligned node for email strategy generation.

    Single responsibility: Generate comprehensive email strategies using LLM-powered agent.
    The graph handles orchestration via conditional edges.

    Features:
    - Integration with StrategyGenerationAgent
    - Circuit breaker pattern for resilience
    - Comprehensive error handling and fallback
    - Enterprise observability and audit trails
    - Defensive programming for LangGraph state conversion
    """

    def __init__(
        self,
        strategy_agent: StrategyGenerationAgent | None = None,
        enable_fallback: bool = True,
        max_timeout: float = 60.0,
    ):
        super().__init__()
        self.strategy_agent = strategy_agent or StrategyGenerationAgent()
        self.enable_fallback = enable_fallback
        self.max_timeout = max_timeout

    def _get_requirements_safely(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> dict[str, Any] | None:
        """Safely extract email requirements using defensive programming."""
        try:
            # Try attribute access first (Pydantic model)
            match state:
                case _ if hasattr(state, "email_requirements"):
                    return state.email_requirements
                case dict():
                    return state.get("email_requirements")
                case _:
                    return None
        except AttributeError:
            # Handle case where state has been converted to dict
            match state:
                case dict():
                    return state.get("email_requirements")
                case _:
                    return None

    def _get_session_id_safely(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> str:
        """Safely extract session ID using defensive programming."""
        try:
            match state:
                case _ if hasattr(state, "session_id"):
                    return state.session_id or "unknown"
                case dict():
                    return state.get("session_id", "unknown")
                case _:
                    return "unknown"
        except AttributeError:
            match state:
                case dict():
                    return state.get("session_id", "unknown")
                case _:
                    return "unknown"

    def _create_fallback_strategy(self, requirements: dict[str, Any]) -> dict[str, Any]:
        """Create fallback strategy when agent fails."""
        recipient_info = requirements.get("recipient", {})
        recipient_name = recipient_info.get("value", "the recipient")
        tone = requirements.get("tone", {}).get("value", "professional")
        purpose = requirements.get("purpose", {}).get("value", "communication")

        return {
            "strategy_summary": f"Fallback strategy for {tone} {purpose} to {recipient_name}",
            "key_messages": [
                "Clear and concise communication",
                "Professional tone throughout",
                "Address recipient's needs",
            ],
            "tone_guidelines": {
                "primary_tone": tone,
                "communication_style": "direct and respectful",
                "formality_level": "professional",
            },
            "structure_recommendation": {
                "opening": "Appropriate greeting and context",
                "body": "Main message with supporting details",
                "closing": "Clear next steps and professional sign-off",
            },
            "success_metrics": [
                "Message clarity",
                "Appropriate tone",
                "Complete information",
            ],
            "generation_method": "fallback",
            "confidence_level": 0.6,
        }

    @traceable(name="strategy_generator_node_execution")
    async def execute(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> UniversalWorkflowState | dict[str, Any]:
        """
        Execute strategy generation with enterprise patterns.

        LangGraph-aligned: Single responsibility execution with defensive programming.

        Args:
            state: Current workflow state (Pydantic model or dict)

        Returns:
            Updated state with generated strategy or error information
        """
        start_time = time.perf_counter()
        session_id = self._get_session_id_safely(state)

        logger.info(
            "strategy_generation_started",
            session_id=session_id,
            node="strategy_generator",
        )

        # Validate requirements are available
        requirements = self._get_requirements_safely(state)
        if not requirements:
            logger.error(
                "strategy_generation_failed_no_requirements",
                session_id=session_id,
            )

            # Update state with error information
            error_updates = {
                "current_node": "requirements_collector",
                "error_message": "Email requirements needed before strategy generation",
                "workflow_phase": WorkflowPhase.BATCH_DISCOVERY.value,
            }

            # Handle both Pydantic and dict state types
            if hasattr(state, "copy"):
                return state.copy(update=error_updates)
            else:
                return {**state, **error_updates}

        try:
            async with asyncio.timeout(self.max_timeout):
                # Generate strategy using the agent
                strategy_result = await self.strategy_agent.execute(
                    requirements, session_id=session_id
                )

                execution_time_ms = (time.perf_counter() - start_time) * 1000

                logger.info(
                    "strategy_generation_completed",
                    session_id=session_id,
                    execution_time_ms=execution_time_ms,
                    agent_used=True,
                )

                # Prepare state updates
                updates = {
                    "email_strategy": strategy_result.get("strategy", {}),
                    "workflow_phase": WorkflowPhase.STRATEGY_CONFIRMATION.value,
                    "current_node": "strategy_confirmation_handler",
                    "strategy_generated_at": datetime.now().isoformat(),
                    "context_data": {
                        **(
                            state.get("context_data", {})
                            if isinstance(state, dict)
                            else state.context_data
                        ),
                        "strategy_generation": {
                            "agent_used": "StrategyGenerationAgent",
                            "generation_method": "llm_powered",
                            "execution_time_ms": execution_time_ms,
                            "confidence_level": strategy_result.get(
                                "confidence_level", 0.8
                            ),
                            "timestamp": datetime.now().isoformat(),
                        },
                    },
                }

                # Handle both Pydantic and dict state types defensively
                if hasattr(state, "copy"):
                    return state.copy(update=updates)
                else:
                    return {**state, **updates}

        except TimeoutError:
            logger.error(
                "strategy_generation_timeout",
                timeout_seconds=self.max_timeout,
                session_id=session_id,
            )

            if self.enable_fallback:
                return await self._handle_fallback(
                    state, requirements, session_id, start_time
                )
            else:
                error_updates = {
                    "error_message": f"Strategy generation timed out after {self.max_timeout}s",
                    "current_node": "error_handler",
                }

                if hasattr(state, "copy"):
                    return state.copy(update=error_updates)
                else:
                    return {**state, **error_updates}

        except Exception as e:
            logger.error(
                "strategy_generation_error",
                error=str(e),
                session_id=session_id,
            )

            if self.enable_fallback:
                return await self._handle_fallback(
                    state, requirements, session_id, start_time
                )
            else:
                error_updates = {
                    "error_message": f"Strategy generation failed: {str(e)}",
                    "current_node": "error_handler",
                }

                if hasattr(state, "copy"):
                    return state.copy(update=error_updates)
                else:
                    return {**state, **error_updates}

    async def _handle_fallback(
        self,
        state: UniversalWorkflowState | dict[str, Any],
        requirements: dict[str, Any],
        session_id: str,
        start_time: float,
    ) -> UniversalWorkflowState | dict[str, Any]:
        """Handle fallback strategy generation."""
        fallback_strategy = self._create_fallback_strategy(requirements)
        execution_time_ms = (time.perf_counter() - start_time) * 1000

        logger.warning(
            "strategy_generation_using_fallback",
            session_id=session_id,
            execution_time_ms=execution_time_ms,
        )

        updates = {
            "email_strategy": fallback_strategy,
            "workflow_phase": WorkflowPhase.STRATEGY_CONFIRMATION.value,
            "current_node": "strategy_confirmation_handler",
            "strategy_generated_at": datetime.now().isoformat(),
            "context_data": {
                **(
                    state.get("context_data", {})
                    if isinstance(state, dict)
                    else state.context_data
                ),
                "strategy_generation": {
                    "agent_used": "fallback",
                    "generation_method": "rule_based_fallback",
                    "execution_time_ms": execution_time_ms,
                    "confidence_level": 0.6,
                    "timestamp": datetime.now().isoformat(),
                },
            },
            "error_message": "Strategy generation failed, using fallback approach",
        }

        if hasattr(state, "copy"):
            return state.copy(update=updates)
        else:
            return {**state, **updates}


# Factory function for workflow integration
def create_strategy_generator_node(
    strategy_agent: StrategyGenerationAgent | None = None,
    **kwargs: Any,
) -> StrategyGeneratorNode:
    """
    Create strategy generator node for LangGraph workflow integration.

    Args:
        strategy_agent: Optional pre-configured strategy agent
        **kwargs: Additional configuration parameters

    Returns:
        Configured StrategyGeneratorNode instance
    """
    return StrategyGeneratorNode(strategy_agent=strategy_agent, **kwargs)
