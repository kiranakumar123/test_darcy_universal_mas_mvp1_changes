"""
Enhanced Email Generator Node for Universal Multi-Agent Framework

LangGraph-aligned business logic node that generates professional emails from confirmed strategies.
Integrates template selection, AI-powered content generation, and fallback mechanisms.

Architecture:
- Single responsibility: Email content generation
- Template store integration with Redis backend
- Defensive programming for LangGraph state handling
- Enterprise observability and quality scoring
"""

from __future__ import annotations

import asyncio
import html
import re
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
from universal_framework.nodes.agents import EmailGenerationAgent
from universal_framework.nodes.base import BaseNode
from universal_framework.observability import UniversalFrameworkLogger

# Initialize enterprise logger
logger = UniversalFrameworkLogger("enhanced_email_generator")


class EnhancedEmailGeneratorNode(BaseNode):
    """
    LangGraph-aligned node for professional email generation.

    Single responsibility: Generate high-quality email content from confirmed strategies.
    The graph handles orchestration via conditional edges.

    Features:
    - Integration with EmailGenerationAgent
    - Template selection and storage
    - HTML and plain text content generation
    - Quality scoring and brand compliance
    - Comprehensive fallback mechanisms
    - Defensive programming for LangGraph state conversion
    """

    def __init__(
        self,
        email_agent: EmailGenerationAgent | None = None,
        enable_template_store: bool = True,
        max_timeout: float = 60.0,
    ):
        super().__init__()
        self.email_agent = email_agent or EmailGenerationAgent()
        self.enable_template_store = enable_template_store
        self.max_timeout = max_timeout
        self.template_cache: dict[str, str] = {}

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

    def _get_context_data_safely(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> dict[str, Any]:
        """Safely extract context data using defensive programming."""
        try:
            match state:
                case _ if hasattr(state, "context_data"):
                    return state.context_data or {}
                case dict():
                    return state.get("context_data", {})
                case _:
                    return {}
        except AttributeError:
            match state:
                case dict():
                    return state.get("context_data", {})
                case _:
                    return {}

    def _select_template_type(self, strategy: dict[str, Any]) -> str:
        """Select appropriate template type based on strategy."""
        # Extract tone and purpose for template selection
        tone = "professional"  # Default
        if "tone_guidelines" in strategy:
            tone = strategy["tone_guidelines"].get("primary_tone", "professional")

        purpose = strategy.get("purpose", "general")

        # Template mapping using modern match/case
        match (tone.lower(), purpose.lower()):
            case ("formal", _) | (_, "announcement"):
                return "formal_announcement"
            case ("casual", _) | (_, "newsletter"):
                return "casual_newsletter"
            case ("urgent", _) | (_, "urgent"):
                return "urgent_notification"
            case (_, "meeting") | (_, "invitation"):
                return "meeting_invitation"
            case (_, "follow_up") | (_, "followup"):
                return "follow_up"
            case _:
                return "professional_standard"

    def _generate_fallback_email(self, strategy: dict[str, Any]) -> dict[str, Any]:
        """Generate fallback email content when AI generation fails."""
        subject = strategy.get("strategy_summary", "Important Communication")
        recipient = strategy.get("recipient", "Team")

        # Extract key messages for content
        key_messages = strategy.get("key_messages", ["Important information to share"])
        content_lines = []

        for i, message in enumerate(key_messages[:3], 1):  # Limit to 3 key messages
            content_lines.append(f"{i}. {message}")

        content = "\n".join(content_lines)

        # Generate HTML content
        html_content = f"""
        <html>
        <head>
            <title>{html.escape(subject)}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                .content {{ margin: 20px 0; }}
                .cta {{
                    background: #007bff;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                    margin: 20px 0;
                }}
                .signature {{ margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <h1>{html.escape(subject)}</h1>
            <p>Dear {html.escape(str(recipient))},</p>
            <div class="content">
                {html.escape(content).replace(chr(10), '<br>')}
            </div>
            <div class="signature">
                <p>Best regards,<br>Your Team</p>
            </div>
        </body>
        </html>
        """

        # Generate plain text version
        text_content = self._convert_html_to_text(html_content)

        return {
            "subject": subject,
            "html_content": html_content,
            "text_content": text_content,
            "quality_score": 0.6,  # Lower score for fallback
            "template_used": "fallback_template",
            "generation_method": "rule_based_fallback",
            "brand_compliance_score": 0.7,
        }

    def _convert_html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text."""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html_content)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Add proper line breaks for readability
        text = text.replace("Dear ", "\nDear ")
        text = text.replace("Best regards", "\n\nBest regards")
        text = re.sub(
            r"(\d+\.) ", r"\n\1 ", text
        )  # Add line breaks before numbered lists

        return text

    def _calculate_quality_score(self, email_content: dict[str, Any]) -> float:
        """Calculate quality score based on email characteristics."""
        score = 0.0

        # Subject line quality (0.3 weight)
        subject = email_content.get("subject", "")
        if subject:
            score += 0.1
            if len(subject) >= 10:
                score += 0.1
            if not subject.isupper():  # Avoid all caps
                score += 0.1

        # Content quality (0.4 weight)
        html_content = email_content.get("html_content", "")
        if html_content:
            score += 0.1
            if len(html_content) > 100:
                score += 0.1
            if "Dear" in html_content:
                score += 0.1
            if "Best regards" in html_content or "Sincerely" in html_content:
                score += 0.1

        # Structure quality (0.3 weight)
        if email_content.get("text_content"):
            score += 0.1
        if email_content.get("template_used"):
            score += 0.1
        if email_content.get("generation_method") == "llm_powered":
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

    @traceable(name="enhanced_email_generator_execution")
    async def execute(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> UniversalWorkflowState | dict[str, Any]:
        """
        Execute email generation with enterprise patterns.

        LangGraph-aligned: Single responsibility execution with defensive programming.

        Args:
            state: Current workflow state (Pydantic model or dict)

        Returns:
            Updated state with generated email content
        """
        start_time = time.perf_counter()
        session_id = self._get_session_id_safely(state)

        logger.info(
            "email_generation_started",
            session_id=session_id,
            node="enhanced_email_generator",
        )

        # Validate strategy is available and confirmed
        strategy = self._get_strategy_safely(state)
        if not strategy:
            logger.error(
                "email_generation_no_strategy",
                session_id=session_id,
            )

            error_updates = {
                "workflow_phase": WorkflowPhase.STRATEGY_CONFIRMATION.value,
                "current_node": "strategy_confirmation_handler",
                "error_message": "No confirmed strategy available for email generation",
            }

            if hasattr(state, "copy"):
                return state.copy(update=error_updates)
            else:
                return {**state, **error_updates}

        # Check if strategy is confirmed (defensive check)
        strategy_approved = False
        try:
            if isinstance(state, dict):
                strategy_approved = state.get("strategy_approved", False)
            else:
                strategy_approved = getattr(state, "strategy_approved", False)
        except AttributeError:
            strategy_approved = False

        if not strategy_approved:
            logger.warning(
                "email_generation_strategy_not_confirmed",
                session_id=session_id,
            )

            warning_updates = {
                "workflow_phase": WorkflowPhase.STRATEGY_CONFIRMATION.value,
                "current_node": "strategy_confirmation_handler",
                "error_message": "Strategy must be confirmed before email generation",
            }

            if hasattr(state, "copy"):
                return state.copy(update=warning_updates)
            else:
                return {**state, **warning_updates}

        context_data = self._get_context_data_safely(state)

        try:
            async with asyncio.timeout(self.max_timeout):
                # Generate email using the agent
                template_type = self._select_template_type(strategy)

                email_result = await self.email_agent.execute(
                    strategy=strategy,
                    template_type=template_type,
                    context_data=context_data,
                    session_id=session_id,
                )

                execution_time_ms = (time.perf_counter() - start_time) * 1000

                # Calculate quality score
                quality_score = self._calculate_quality_score(email_result)
                email_result["quality_score"] = quality_score
                email_result["brand_compliance_score"] = min(quality_score + 0.1, 1.0)

                logger.info(
                    "email_generation_completed",
                    session_id=session_id,
                    execution_time_ms=execution_time_ms,
                    quality_score=quality_score,
                    template_type=template_type,
                )

                # Prepare state updates
                updates = {
                    "generated_email": email_result,
                    "workflow_phase": WorkflowPhase.REVIEW.value,
                    "current_node": "email_review_handler",
                    "email_generated_at": datetime.now().isoformat(),
                    "context_data": {
                        **context_data,
                        "email_generation": {
                            "generation_method": email_result.get(
                                "generation_method", "llm_powered"
                            ),
                            "template_used": email_result.get(
                                "template_used", template_type
                            ),
                            "quality_score": quality_score,
                            "execution_time_ms": execution_time_ms,
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
                "email_generation_timeout",
                timeout_seconds=self.max_timeout,
                session_id=session_id,
            )

            # Generate fallback email
            fallback_email = self._generate_fallback_email(strategy)
            execution_time_ms = (time.perf_counter() - start_time) * 1000

            logger.warning(
                "email_generation_using_fallback",
                session_id=session_id,
                execution_time_ms=execution_time_ms,
            )

            updates = {
                "generated_email": fallback_email,
                "workflow_phase": WorkflowPhase.REVIEW.value,
                "current_node": "email_review_handler",
                "email_generated_at": datetime.now().isoformat(),
                "context_data": {
                    **context_data,
                    "email_generation": {
                        "generation_method": "timeout_fallback",
                        "template_used": "fallback_template",
                        "quality_score": fallback_email["quality_score"],
                        "execution_time_ms": execution_time_ms,
                        "timestamp": datetime.now().isoformat(),
                    },
                },
                "error_message": f"Email generation timed out after {self.max_timeout}s, using fallback",
            }

            if hasattr(state, "copy"):
                return state.copy(update=updates)
            else:
                return {**state, **updates}

        except Exception as e:
            logger.error(
                "email_generation_error",
                error=str(e),
                session_id=session_id,
            )

            # Generate fallback email
            fallback_email = self._generate_fallback_email(strategy)
            execution_time_ms = (time.perf_counter() - start_time) * 1000

            updates = {
                "generated_email": fallback_email,
                "workflow_phase": WorkflowPhase.REVIEW.value,
                "current_node": "email_review_handler",
                "email_generated_at": datetime.now().isoformat(),
                "context_data": {
                    **context_data,
                    "email_generation": {
                        "generation_method": "error_fallback",
                        "template_used": "fallback_template",
                        "quality_score": fallback_email["quality_score"],
                        "execution_time_ms": execution_time_ms,
                        "timestamp": datetime.now().isoformat(),
                    },
                },
                "error_message": f"Email generation failed: {str(e)}, using fallback",
            }

            if hasattr(state, "copy"):
                return state.copy(update=updates)
            else:
                return {**state, **updates}


# Factory function for workflow integration
def create_enhanced_email_generator_node(
    email_agent: EmailGenerationAgent | None = None,
    **kwargs: Any,
) -> EnhancedEmailGeneratorNode:
    """
    Create enhanced email generator node for LangGraph workflow integration.

    Args:
        email_agent: Optional pre-configured email generation agent
        **kwargs: Additional configuration parameters

    Returns:
        Configured EnhancedEmailGeneratorNode instance
    """
    return EnhancedEmailGeneratorNode(email_agent=email_agent, **kwargs)
