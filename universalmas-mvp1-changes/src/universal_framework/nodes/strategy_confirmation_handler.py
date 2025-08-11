"""
Strategy Confirmation Handler for Universal Multi-Agent Framework

LangGraph-aligned business logic node that handles strategy confirmation workflow.
Processes user feedback on generated strategies with enterprise patterns.

Architecture:
- Single responsibility: Strategy confirmation and modification logic
- User choice parsing with LLM-powered analysis
- Defensive programming for LangGraph state handling
- Enterprise observability and audit trails
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
from universal_framework.llm.providers import LLMProvider, create_default_provider
from universal_framework.nodes.base import BaseNode
from universal_framework.observability import UniversalFrameworkLogger

# Initialize enterprise logger
logger = UniversalFrameworkLogger("strategy_confirmation_node")


class StrategyConfirmationHandler(BaseNode):
    """
    LangGraph-aligned node for strategy confirmation workflow.

    Single responsibility: Handle user feedback on generated strategies.
    The graph handles orchestration via conditional edges.

    Features:
    - LLM-powered user choice parsing
    - Strategy modification support
    - Enterprise audit trails
    - Defensive programming for LangGraph state conversion
    - Comprehensive error handling
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        max_timeout: float = 30.0,
        max_modification_attempts: int = 3,
    ):
        super().__init__()
        self.llm_provider = llm_provider or create_default_provider()
        self.max_timeout = max_timeout
        self.max_modification_attempts = max_modification_attempts

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

    def _get_strategy_safely(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> dict[str, Any] | None:
        """Safely extract email strategy using defensive programming."""
        try:
            match state:
                case _ if hasattr(state, "email_strategy"):
                    return state.email_strategy
                case dict():
                    return state.get("email_strategy")
                case _:
                    return None
        except AttributeError:
            match state:
                case dict():
                    return state.get("email_strategy")
                case _:
                    return None

    def _get_messages_safely(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> list[Any]:
        """Safely extract messages using defensive programming."""
        try:
            match state:
                case _ if hasattr(state, "messages"):
                    return state.messages or []
                case dict():
                    return state.get("messages", [])
                case _:
                    return []
        except AttributeError:
            match state:
                case dict():
                    return state.get("messages", [])
                case _:
                    return []

    def _extract_user_message(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> str | None:
        """Extract the most recent user message from state."""
        messages = self._get_messages_safely(state)

        for message in reversed(messages):
            # Handle different message formats defensively
            try:
                match message:
                    case _ if hasattr(message, "sender") and message.sender == "user":
                        return message.content
                    case _ if hasattr(message, "type") and message.type == "human":
                        return message.content
                    case dict() if (
                        message.get("sender") == "user"
                        or message.get("type") == "human"
                    ):
                        return message.get("content", "")
            except (AttributeError, TypeError):
                continue

        return None

    async def _parse_user_choice(self, message: str) -> str:
        """Parse user choice using LLM analysis with fallback to pattern matching."""
        try:
            # LLM-powered choice analysis
            llm = self.llm_provider.create_agent_llm()

            prompt = f"""Analyze this user message about a strategy and determine their choice:

User message: "{message}"

Classify as exactly one of:
- "approve" - User approves/accepts the strategy
- "modify" - User wants changes/modifications to the strategy
- "reject" - User rejects/disagrees with the strategy entirely
- "ambiguous" - Cannot determine clear intent

Only respond with the single word classification."""

            response = await llm.ainvoke(prompt)
            choice = response.content.strip().lower()

            if choice in ["approve", "modify", "reject", "ambiguous"]:
                return choice

        except Exception as e:
            logger.warning(
                "llm_choice_parsing_failed",
                error=str(e),
                fallback="pattern_matching",
            )

        # Fallback to pattern matching
        message_lower = message.lower().strip()

        # Approval patterns
        approval_patterns = [
            "approve",
            "accept",
            "yes",
            "looks good",
            "proceed",
            "go ahead",
        ]
        if any(pattern in message_lower for pattern in approval_patterns):
            return "approve"

        # Rejection patterns
        rejection_patterns = [
            "reject",
            "no",
            "disagree",
            "start over",
            "completely wrong",
        ]
        if any(pattern in message_lower for pattern in rejection_patterns):
            return "reject"

        # Modification patterns
        modification_patterns = [
            "modify",
            "change",
            "adjust",
            "update",
            "revise",
            "but",
        ]
        if any(pattern in message_lower for pattern in modification_patterns):
            return "modify"

        return "ambiguous"

    async def _parse_modification_requests(self, message: str) -> dict[str, str]:
        """Parse specific modification requests from user message."""
        try:
            llm = self.llm_provider.create_agent_llm()

            prompt = f"""Extract specific modification requests from this user message:

User message: "{message}"

Identify any requested changes to:
- tone (formal, casual, professional, friendly)
- timing (urgent, immediate, gradual, phased)
- approach (direct, diplomatic, collaborative)
- content (brief, detailed, comprehensive)

Return as JSON with only the modifications mentioned:
{{"tone": "requested tone", "timing": "requested timing", etc.}}

If no specific modifications are mentioned, return: {{}}"""

            response = await llm.ainvoke(prompt)

            # Simple JSON parsing with fallback
            try:
                import json

                modifications = json.loads(response.content.strip())
                if isinstance(modifications, dict):
                    return modifications
            except (json.JSONDecodeError, AttributeError, TypeError):
                # Parsing failed, continue to return empty dict
                pass

        except Exception as e:
            logger.warning(
                "modification_parsing_failed",
                error=str(e),
                fallback="empty_dict",
            )

        return {}

    def _apply_modifications(
        self, strategy: dict[str, Any], modifications: dict[str, str]
    ) -> dict[str, Any]:
        """Apply modifications to strategy."""
        updated_strategy = strategy.copy()

        for mod_type, mod_value in modifications.items():
            match mod_type.lower():
                case "tone":
                    updated_strategy["tone_guidelines"] = updated_strategy.get(
                        "tone_guidelines", {}
                    )
                    updated_strategy["tone_guidelines"]["primary_tone"] = mod_value
                case "timing":
                    match mod_value.lower():
                        case value if "urgent" in value or "immediate" in value:
                            updated_strategy["timeline"] = "immediate"
                        case value if "gradual" in value or "phased" in value:
                            updated_strategy["timeline"] = "phased"
                case "approach":
                    updated_strategy["primary_approach"] = mod_value
                case "content":
                    updated_strategy["content_style"] = mod_value

        # Update modification timestamp
        updated_strategy["last_modified"] = datetime.now().isoformat()

        return updated_strategy

    def _create_strategy_summary(self, strategy: dict[str, Any]) -> str:
        """Create readable strategy summary for user display."""
        if not strategy:
            return "No strategy available"

        summary_parts = []

        if "strategy_summary" in strategy:
            summary_parts.append(f"**Strategy:** {strategy['strategy_summary']}")

        if (
            "tone_guidelines" in strategy
            and "primary_tone" in strategy["tone_guidelines"]
        ):
            summary_parts.append(
                f"**Tone:** {strategy['tone_guidelines']['primary_tone']}"
            )

        if "timeline" in strategy:
            summary_parts.append(f"**Timeline:** {strategy['timeline']}")

        if "primary_approach" in strategy:
            summary_parts.append(f"**Approach:** {strategy['primary_approach']}")

        return (
            "\n".join(summary_parts) if summary_parts else "Strategy details available"
        )

    @traceable(name="strategy_confirmation_node_execution")
    async def execute(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> UniversalWorkflowState | dict[str, Any]:
        """
        Execute strategy confirmation workflow.

        LangGraph-aligned: Single responsibility execution with defensive programming.

        Args:
            state: Current workflow state (Pydantic model or dict)

        Returns:
            Updated state with confirmation results
        """
        start_time = time.perf_counter()
        session_id = self._get_session_id_safely(state)

        logger.info(
            "strategy_confirmation_started",
            session_id=session_id,
            node="strategy_confirmation_node",
        )

        # Validate strategy is available
        strategy = self._get_strategy_safely(state)
        if not strategy:
            logger.error(
                "strategy_confirmation_no_strategy",
                session_id=session_id,
            )

            error_updates = {
                "workflow_phase": WorkflowPhase.STRATEGY_ANALYSIS.value,
                "current_node": "strategy_generator",
                "error_message": "No strategy available for confirmation",
            }

            if hasattr(state, "copy"):
                return state.copy(update=error_updates)
            else:
                return {**state, **error_updates}

        # Extract user message
        user_message = self._extract_user_message(state)
        if not user_message:
            # Request user input
            request_updates = {
                "user_message": (
                    f"Please review the proposed strategy:\n\n"
                    f"{self._create_strategy_summary(strategy)}\n\n"
                    f"Do you approve, want modifications, or reject this strategy?"
                ),
                "message_type": "strategy_confirmation_request",
                "requires_input": True,
                "suggestions": [
                    "Approve",
                    "I want to modify the tone",
                    "Reject and start over",
                ],
            }

            if hasattr(state, "copy"):
                return state.copy(update=request_updates)
            else:
                return {**state, **request_updates}

        try:
            async with asyncio.timeout(self.max_timeout):
                # Parse user choice
                choice = await self._parse_user_choice(user_message)
                execution_time_ms = (time.perf_counter() - start_time) * 1000

                logger.info(
                    "strategy_confirmation_choice_parsed",
                    choice=choice,
                    session_id=session_id,
                    execution_time_ms=execution_time_ms,
                )

                # Handle choice using modern match/case
                match choice:
                    case "approve":
                        return await self._handle_approval(state, strategy, session_id)
                    case "modify":
                        return await self._handle_modification(
                            state, strategy, user_message, session_id
                        )
                    case "reject":
                        return await self._handle_rejection(state, session_id)
                    case _:
                        return await self._handle_ambiguous_input(
                            state, user_message, session_id
                        )

        except TimeoutError:
            logger.error(
                "strategy_confirmation_timeout",
                timeout_seconds=self.max_timeout,
                session_id=session_id,
            )

            timeout_updates = {
                "error_message": f"Strategy confirmation timed out after {self.max_timeout}s",
                "current_node": "error_handler",
            }

            if hasattr(state, "copy"):
                return state.copy(update=timeout_updates)
            else:
                return {**state, **timeout_updates}

        except Exception as e:
            logger.error(
                "strategy_confirmation_error",
                error=str(e),
                session_id=session_id,
            )

            error_updates = {
                "error_message": f"Strategy confirmation failed: {str(e)}",
                "current_node": "error_handler",
            }

            if hasattr(state, "copy"):
                return state.copy(update=error_updates)
            else:
                return {**state, **error_updates}

    async def _handle_approval(
        self,
        state: UniversalWorkflowState | dict[str, Any],
        strategy: dict[str, Any],
        session_id: str,
    ) -> UniversalWorkflowState | dict[str, Any]:
        """Handle strategy approval."""
        logger.info(
            "strategy_approved",
            session_id=session_id,
        )

        updates = {
            "user_message": (
                "✅ Strategy approved! Proceeding to email generation with your confirmed strategy:\n\n"
                f"{self._create_strategy_summary(strategy)}\n\n"
                "Moving to content generation phase..."
            ),
            "message_type": "strategy_approved",
            "strategy_approved": True,
            "workflow_phase": WorkflowPhase.GENERATION.value,
            "current_node": "email_generator",
            "requires_input": False,
            "context_data": {
                **(
                    state.get("context_data", {})
                    if isinstance(state, dict)
                    else state.context_data
                ),
                "strategy_approved_at": datetime.now().isoformat(),
                "approval_audit": {
                    "action": "approve",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                },
            },
        }

        if hasattr(state, "copy"):
            return state.copy(update=updates)
        else:
            return {**state, **updates}

    async def _handle_modification(
        self,
        state: UniversalWorkflowState | dict[str, Any],
        strategy: dict[str, Any],
        user_message: str,
        session_id: str,
    ) -> UniversalWorkflowState | dict[str, Any]:
        """Handle strategy modification request."""
        modifications = await self._parse_modification_requests(user_message)
        modified_strategy = self._apply_modifications(strategy, modifications)

        logger.info(
            "strategy_modified",
            modifications=list(modifications.keys()),
            session_id=session_id,
        )

        updates = {
            "user_message": (
                "🔄 Strategy updated based on your feedback:\n\n"
                f"{self._create_strategy_summary(modified_strategy)}\n\n"
                f"**Changes Made:** {', '.join(modifications.keys()) if modifications else 'General adjustments'}\n\n"
                "Does this revised strategy look good? (approve/modify further/reject)"
            ),
            "message_type": "strategy_modified",
            "email_strategy": modified_strategy,
            "requires_input": True,
            "suggestions": ["Approve", "Make more changes", "Reject"],
            "context_data": {
                **(
                    state.get("context_data", {})
                    if isinstance(state, dict)
                    else state.context_data
                ),
                "last_modification_at": datetime.now().isoformat(),
                "modification_count": (
                    state.get("context_data", {}).get("modification_count", 0)
                    if isinstance(state, dict)
                    else state.context_data.get("modification_count", 0)
                )
                + 1,
                "modification_audit": {
                    "action": "modify",
                    "timestamp": datetime.now().isoformat(),
                    "modifications": modifications,
                    "session_id": session_id,
                },
            },
        }

        if hasattr(state, "copy"):
            return state.copy(update=updates)
        else:
            return {**state, **updates}

    async def _handle_rejection(
        self,
        state: UniversalWorkflowState | dict[str, Any],
        session_id: str,
    ) -> UniversalWorkflowState | dict[str, Any]:
        """Handle strategy rejection."""
        logger.info(
            "strategy_rejected",
            session_id=session_id,
        )

        updates = {
            "user_message": (
                "❌ Strategy rejected. I'll generate a new strategy based on your requirements.\n\n"
                "Please provide additional guidance for the new strategy, or I'll create an alternative approach."
            ),
            "message_type": "strategy_rejected",
            "strategy_approved": False,
            "workflow_phase": WorkflowPhase.STRATEGY_ANALYSIS.value,
            "current_node": "strategy_generator",
            "email_strategy": None,
            "requires_input": True,
            "suggestions": [
                "Generate a different approach",
                "Provide more specific requirements",
            ],
            "context_data": {
                **(
                    state.get("context_data", {})
                    if isinstance(state, dict)
                    else state.context_data
                ),
                "strategy_rejected_at": datetime.now().isoformat(),
                "rejection_audit": {
                    "action": "reject",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                },
            },
        }

        if hasattr(state, "copy"):
            return state.copy(update=updates)
        else:
            return {**state, **updates}

    async def _handle_ambiguous_input(
        self,
        state: UniversalWorkflowState | dict[str, Any],
        user_message: str,
        session_id: str,
    ) -> UniversalWorkflowState | dict[str, Any]:
        """Handle ambiguous user input."""
        logger.warning(
            "strategy_confirmation_ambiguous_input",
            user_message=user_message[:100],
            session_id=session_id,
        )

        updates = {
            "user_message": (
                "I couldn't understand if you approve, want modifications, or reject the strategy. "
                "Please clarify your choice:\n\n"
                "• **Approve** - Use this strategy as-is\n"
                "• **Modify** - Make specific changes (tell me what to adjust)\n"
                "• **Reject** - Start over with a new strategy"
            ),
            "message_type": "clarification_request",
            "requires_input": True,
            "suggestions": [
                "Approve",
                "Modify the tone to be more formal",
                "Reject and start over",
            ],
            "context_data": {
                **(
                    state.get("context_data", {})
                    if isinstance(state, dict)
                    else state.context_data
                ),
                "ambiguous_input": user_message,
                "clarification_requested_at": datetime.now().isoformat(),
            },
        }

        if hasattr(state, "copy"):
            return state.copy(update=updates)
        else:
            return {**state, **updates}


# Factory function for workflow integration
def create_strategy_confirmation_handler(
    llm_provider: LLMProvider | None = None,
    **kwargs: Any,
) -> StrategyConfirmationHandler:
    """
    Create strategy confirmation handler for LangGraph workflow integration.

    Args:
        llm_provider: Optional pre-configured LLM provider
        **kwargs: Additional configuration parameters

    Returns:
        Configured StrategyConfirmationHandler instance
    """
    return StrategyConfirmationHandler(llm_provider=llm_provider, **kwargs)
