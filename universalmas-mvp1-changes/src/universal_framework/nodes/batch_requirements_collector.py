"""
Batch Requirements Collector Node for Universal Multi-Agent Framework

LangGraph-aligned business logic node that collects and validates email requirements
from user input using modern Python 3.11+ patterns and enterprise observability.

Architecture:
- Single responsibility: Requirements collection and validation
- Integration with RequirementsCollectionAgent
- Defensive programming for LangGraph state handling
- Enterprise observability and audit trails
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
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
from universal_framework.nodes.agents import RequirementsCollectionAgent
from universal_framework.nodes.base import BaseNode
from universal_framework.observability import UniversalFrameworkLogger

# Initialize enterprise logger
logger = UniversalFrameworkLogger("batch_requirements_collector")


class ExtractionMethod(Enum):
    """Methods used to extract requirements."""

    LLM_POWERED = auto()
    PATTERN_BASED = auto()
    ERROR_RECOVERY = auto()


class CompletionLevel(Enum):
    """Levels of requirement completeness."""

    EXCELLENT = auto()  # 90%+ complete
    GOOD = auto()  # 70-90% complete
    BASIC = auto()  # 50-70% complete
    INCOMPLETE = auto()  # <50% complete


@dataclass(frozen=True)
class ExtractionResult:
    """Result of requirements extraction process."""

    requirements: dict[str, Any]
    completeness_score: float
    missing_fields: list[str]
    extraction_method: ExtractionMethod
    completion_level: CompletionLevel
    errors: list[str]


class BatchRequirementsCollectorNode(BaseNode):
    """
    LangGraph-aligned node for batch requirements collection.

    Single responsibility: Collect and validate email requirements from user input.
    The graph handles orchestration via conditional edges.

    Features:
    - Integration with RequirementsCollectionAgent
    - Multi-method extraction (LLM -> Pattern -> Recovery)
    - Completeness scoring and validation
    - Defensive programming for LangGraph state conversion
    - Enterprise observability and audit trails
    """

    def __init__(
        self,
        requirements_agent: RequirementsCollectionAgent | None = None,
        min_completeness_threshold: float = 0.6,
        max_timeout: float = 45.0,
    ):
        super().__init__()
        self.requirements_agent = requirements_agent or RequirementsCollectionAgent()
        self.min_completeness_threshold = min_completeness_threshold
        self.max_timeout = max_timeout

        # Field weights for completeness scoring
        self.field_weights = {
            "recipient": 0.25,  # Who to send to
            "purpose": 0.20,  # Why sending
            "subject": 0.15,  # Email subject
            "key_points": 0.15,  # Main content points
            "tone": 0.10,  # Communication style
            "call_to_action": 0.10,  # What recipient should do
            "deadline": 0.05,  # Time sensitivity
        }

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

    def _get_user_input_safely(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> str | None:
        """Safely extract user input from state."""
        try:
            # Check for user_message field first
            match state:
                case _ if hasattr(state, "user_message") and state.user_message:
                    return state.user_message
                case dict() if state.get("user_message"):
                    return state.get("user_message")

            # Check messages for user input
            messages = []
            match state:
                case _ if hasattr(state, "messages"):
                    messages = state.messages or []
                case dict():
                    messages = state.get("messages", [])

            # Find most recent user message
            for message in reversed(messages):
                try:
                    if hasattr(message, "sender") and message.sender == "user":
                        return message.content
                    elif hasattr(message, "type") and message.type == "human":
                        return message.content
                    elif isinstance(message, dict):
                        if (
                            message.get("sender") == "user"
                            or message.get("type") == "human"
                        ):
                            return message.get("content", "")
                except (AttributeError, TypeError):
                    continue

            return None

        except AttributeError:
            match state:
                case dict():
                    return state.get("user_message")
                case _:
                    return None

    def _calculate_completeness_score(
        self, requirements: dict[str, Any]
    ) -> tuple[float, list[str], CompletionLevel]:
        """Calculate completeness score and identify missing fields."""
        total_score = 0.0
        missing_fields = []

        for field, weight in self.field_weights.items():
            field_value = requirements.get(field, {})

            # Check if field has meaningful content
            if isinstance(field_value, dict):
                value = field_value.get("value", "")
                confidence = field_value.get("confidence", 0.0)
            else:
                value = str(field_value) if field_value else ""
                confidence = 1.0 if value else 0.0

            if value and value.strip() and confidence > 0.3:
                total_score += weight
            else:
                missing_fields.append(field)

        # Determine completion level using modern match/case
        match total_score:
            case score if score >= 0.9:
                level = CompletionLevel.EXCELLENT
            case score if score >= 0.7:
                level = CompletionLevel.GOOD
            case score if score >= 0.5:
                level = CompletionLevel.BASIC
            case _:
                level = CompletionLevel.INCOMPLETE

        return total_score, missing_fields, level

    def _extract_with_patterns(self, user_input: str) -> dict[str, Any]:
        """Fallback pattern-based extraction when LLM fails."""
        import re

        requirements = {}

        # Email patterns
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = re.findall(email_pattern, user_input, re.IGNORECASE)
        if emails:
            requirements["recipient"] = {
                "value": ", ".join(emails),
                "confidence": 0.9,
                "extraction_method": "pattern_matching",
            }

        # Subject patterns
        subject_patterns = [
            r"subject[:\s]+([^\n\r]+)",
            r"about[:\s]+([^\n\r]+)",
            r"regarding[:\s]+([^\n\r]+)",
        ]
        for pattern in subject_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                requirements["subject"] = {
                    "value": match.group(1).strip(),
                    "confidence": 0.8,
                    "extraction_method": "pattern_matching",
                }
                break

        # Purpose keywords
        purpose_keywords = {
            "meeting": "schedule meeting",
            "update": "provide update",
            "announcement": "make announcement",
            "invitation": "send invitation",
            "follow": "follow up",
            "reminder": "send reminder",
        }

        user_lower = user_input.lower()
        for keyword, purpose in purpose_keywords.items():
            if keyword in user_lower:
                requirements["purpose"] = {
                    "value": purpose,
                    "confidence": 0.7,
                    "extraction_method": "keyword_matching",
                }
                break

        # Tone detection
        tone_indicators = {
            "formal": ["formal", "professional", "official"],
            "casual": ["casual", "informal", "friendly"],
            "urgent": ["urgent", "asap", "immediately", "priority"],
        }

        for tone, indicators in tone_indicators.items():
            if any(indicator in user_lower for indicator in indicators):
                requirements["tone"] = {
                    "value": tone,
                    "confidence": 0.8,
                    "extraction_method": "keyword_matching",
                }
                break

        return requirements

    def _create_error_recovery_requirements(self, user_input: str) -> dict[str, Any]:
        """Create minimal requirements from user input when all extraction fails."""
        return {
            "recipient": {
                "value": "team",
                "confidence": 0.3,
                "extraction_method": "error_recovery",
            },
            "purpose": {
                "value": "general communication",
                "confidence": 0.3,
                "extraction_method": "error_recovery",
            },
            "subject": {
                "value": "Important Communication",
                "confidence": 0.3,
                "extraction_method": "error_recovery",
            },
            "key_points": {
                "value": (
                    user_input[:200] + "..." if len(user_input) > 200 else user_input
                ),
                "confidence": 0.5,
                "extraction_method": "error_recovery",
            },
            "tone": {
                "value": "professional",
                "confidence": 0.4,
                "extraction_method": "error_recovery",
            },
        }

    @traceable(name="batch_requirements_collector_execution")
    async def execute(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> UniversalWorkflowState | dict[str, Any]:
        """
        Execute requirements collection with multi-method extraction.

        LangGraph-aligned: Single responsibility execution with defensive programming.

        Args:
            state: Current workflow state (Pydantic model or dict)

        Returns:
            Updated state with extracted requirements or request for more input
        """
        start_time = time.perf_counter()
        session_id = self._get_session_id_safely(state)

        logger.info(
            "requirements_collection_started",
            session_id=session_id,
            node="batch_requirements_collector",
        )

        # Extract user input
        user_input = self._get_user_input_safely(state)
        if not user_input or not user_input.strip():
            # Request user input
            request_updates = {
                "user_message": (
                    "I'd be happy to help you create an email! To get started, please tell me:\n\n"
                    "• **Who** you're sending this to\n"
                    "• **What** the email is about\n"
                    "• **Why** you're sending it\n\n"
                    "For example: 'I need to email my team about the project deadline extension'"
                ),
                "message_type": "requirements_request",
                "requires_input": True,
                "suggestions": [
                    "Email my team about the meeting",
                    "Send announcement to all staff",
                    "Follow up with client on proposal",
                ],
            }

            if hasattr(state, "copy"):
                return state.copy(update=request_updates)
            else:
                return {**state, **request_updates}

        try:
            async with asyncio.timeout(self.max_timeout):
                extraction_result = await self._extract_requirements_with_fallback(
                    user_input, session_id
                )

                execution_time_ms = (time.perf_counter() - start_time) * 1000

                logger.info(
                    "requirements_extraction_completed",
                    session_id=session_id,
                    completeness_score=extraction_result.completeness_score,
                    completion_level=extraction_result.completion_level.name,
                    extraction_method=extraction_result.extraction_method.name,
                    execution_time_ms=execution_time_ms,
                )

                # Check if requirements are sufficient
                if (
                    extraction_result.completeness_score
                    >= self.min_completeness_threshold
                ):
                    # Sufficient requirements - proceed to strategy
                    updates = {
                        "email_requirements": extraction_result.requirements,
                        "workflow_phase": WorkflowPhase.STRATEGY_ANALYSIS.value,
                        "current_node": "strategy_generator",
                        "requirements_collected_at": datetime.now().isoformat(),
                        "context_data": {
                            **(
                                state.get("context_data", {})
                                if isinstance(state, dict)
                                else state.context_data
                            ),
                            "requirements_extraction": {
                                "completeness_score": extraction_result.completeness_score,
                                "completion_level": extraction_result.completion_level.name,
                                "extraction_method": extraction_result.extraction_method.name,
                                "execution_time_ms": execution_time_ms,
                                "timestamp": datetime.now().isoformat(),
                            },
                        },
                    }
                else:
                    # Insufficient requirements - ask for more details
                    missing_fields_text = ", ".join(extraction_result.missing_fields)
                    updates = {
                        "user_message": (
                            f"I've captured some details about your email, but I need more information to create the best content:\n\n"
                            f"**Currently missing:** {missing_fields_text}\n\n"
                            f"Could you please provide more details about these aspects?"
                        ),
                        "message_type": "requirements_clarification",
                        "requires_input": True,
                        "suggestions": [
                            "Add recipient details",
                            "Clarify the purpose",
                            "Specify the tone needed",
                        ],
                        "partial_requirements": extraction_result.requirements,
                        "context_data": {
                            **(
                                state.get("context_data", {})
                                if isinstance(state, dict)
                                else state.context_data
                            ),
                            "requirements_extraction": {
                                "completeness_score": extraction_result.completeness_score,
                                "missing_fields": extraction_result.missing_fields,
                                "extraction_method": extraction_result.extraction_method.name,
                                "execution_time_ms": execution_time_ms,
                                "timestamp": datetime.now().isoformat(),
                            },
                        },
                    }

                if hasattr(state, "copy"):
                    return state.copy(update=updates)
                else:
                    return {**state, **updates}

        except TimeoutError:
            logger.error(
                "requirements_collection_timeout",
                timeout_seconds=self.max_timeout,
                session_id=session_id,
            )

            timeout_updates = {
                "error_message": f"Requirements collection timed out after {self.max_timeout}s",
                "current_node": "error_handler",
            }

            if hasattr(state, "copy"):
                return state.copy(update=timeout_updates)
            else:
                return {**state, **timeout_updates}

        except Exception as e:
            logger.error(
                "requirements_collection_error",
                error=str(e),
                session_id=session_id,
            )

            error_updates = {
                "error_message": f"Requirements collection failed: {str(e)}",
                "current_node": "error_handler",
            }

            if hasattr(state, "copy"):
                return state.copy(update=error_updates)
            else:
                return {**state, **error_updates}

    async def _extract_requirements_with_fallback(
        self, user_input: str, session_id: str
    ) -> ExtractionResult:
        """Extract requirements with multi-method fallback."""
        errors = []

        # Method 1: LLM-powered extraction
        try:
            requirements = await self.requirements_agent.execute(
                user_input, session_id=session_id
            )

            if requirements and requirements.get("requirements"):
                req_data = requirements["requirements"]
                completeness_score, missing_fields, completion_level = (
                    self._calculate_completeness_score(req_data)
                )

                return ExtractionResult(
                    requirements=req_data,
                    completeness_score=completeness_score,
                    missing_fields=missing_fields,
                    extraction_method=ExtractionMethod.LLM_POWERED,
                    completion_level=completion_level,
                    errors=[],
                )

        except Exception as e:
            errors.append(str(e))
            logger.warning(
                "llm_extraction_failed",
                error=str(e),
                fallback="pattern_based",
                session_id=session_id,
            )

        # Method 2: Pattern-based extraction
        try:
            requirements = self._extract_with_patterns(user_input)
            completeness_score, missing_fields, completion_level = (
                self._calculate_completeness_score(requirements)
            )

            return ExtractionResult(
                requirements=requirements,
                completeness_score=completeness_score,
                missing_fields=missing_fields,
                extraction_method=ExtractionMethod.PATTERN_BASED,
                completion_level=completion_level,
                errors=errors,
            )

        except Exception as e:
            errors.append(str(e))
            logger.warning(
                "pattern_extraction_failed",
                error=str(e),
                fallback="error_recovery",
                session_id=session_id,
            )

        # Method 3: Error recovery
        requirements = self._create_error_recovery_requirements(user_input)
        completeness_score, missing_fields, completion_level = (
            self._calculate_completeness_score(requirements)
        )

        return ExtractionResult(
            requirements=requirements,
            completeness_score=completeness_score,
            missing_fields=missing_fields,
            extraction_method=ExtractionMethod.ERROR_RECOVERY,
            completion_level=completion_level,
            errors=errors,
        )


# Factory function for workflow integration
def create_batch_requirements_collector_node(
    requirements_agent: RequirementsCollectionAgent | None = None,
    **kwargs: Any,
) -> BatchRequirementsCollectorNode:
    """
    Create batch requirements collector node for LangGraph workflow integration.

    Args:
        requirements_agent: Optional pre-configured requirements collection agent
        **kwargs: Additional configuration parameters

    Returns:
        Configured BatchRequirementsCollectorNode instance
    """
    return BatchRequirementsCollectorNode(
        requirements_agent=requirements_agent, **kwargs
    )
