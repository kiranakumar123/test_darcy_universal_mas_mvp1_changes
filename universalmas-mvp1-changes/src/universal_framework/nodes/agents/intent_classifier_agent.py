"""
Intent Classification Agent for Universal Multi-Agent System

LangGraph-aligned agent for routing users to appropriate workflows
with enterprise-grade classification using modern Python 3.11+ patterns.

Features:
- Multi-tier classification: Conversation-aware -> LLM -> Pattern fallback
- Async-first architecture with timeout and retry support
- Defensive programming for LangGraph state handling
- Enterprise observability and audit management
"""

from __future__ import annotations

import asyncio
import re
import time
from enum import Enum
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from universal_framework.observability import UniversalFrameworkLogger

from ...compliance import PrivacySafeLogger
from ...compliance.audit_manager import EnterpriseAuditManager
from ...config.feature_flags import feature_flags
from ...contracts.state import UniversalWorkflowState
from ...llm.providers import LLMConfig
from .intent_analysis_agent import IntentAnalysisAgent

# Conditional LangSmith tracing following established patterns
try:
    if feature_flags.is_enabled("LANGSMITH_TRACING"):
        from langsmith import traceable

        _LANGSMITH_AVAILABLE = True
    else:

        def traceable(name: str = None, **kwargs):
            def decorator(func):
                return func

            return decorator

        _LANGSMITH_AVAILABLE = False
except ImportError:

    def traceable(name: str = None, **kwargs):
        def decorator(func):
            return func

        return decorator

    _LANGSMITH_AVAILABLE = False

# Initialize enterprise logger
logger = UniversalFrameworkLogger("intent_classifier_agent")


class UserIntent(Enum):
    """Supported user intents for workflow routing."""

    EMAIL_REQUEST = "email_request"
    HELP_REQUEST = "help_request"
    GREETING = "greeting"
    OCM_COMMUNICATION = "ocm_communication"
    DOCUMENT_GENERATION = "document_generation"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    PROCESS_OPTIMIZATION = "process_optimization"
    CAPABILITIES_INQUIRY = "capabilities_inquiry"
    UNCLEAR = "unclear"
    INVALID = "invalid"


class IntentClassificationResult(BaseModel):
    """Structured output for LLM-based intent classification."""

    intent: UserIntent = Field(description="The classified user intent")
    confidence: float = Field(description="Classification confidence 0.0-1.0")
    reasoning: str = Field(description="Brief explanation of classification")


class IntentClassifierAgent:
    """
    Enterprise-grade intent classifier for workflow routing.

    LangGraph-aligned: Single responsibility for intent classification.
    The graph handles orchestration via conditional edges, not this node.

    Features:
    - Multi-tier classification strategy
    - Async-first architecture with modern Python 3.11+
    - Enterprise logging and observability
    - Defensive programming for LangGraph state handling
    """

    def __init__(
        self,
        llm: ChatOpenAI | None = None,
        enable_conversation_aware: bool = True,
        max_timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.llm = llm or self._create_default_llm()
        self.max_timeout = max_timeout
        self.max_retries = max_retries

        # Initialize conversation-aware classifier if enabled
        self.conversation_aware_classifier = None
        if enable_conversation_aware:
            try:
                self.conversation_aware_classifier = IntentAnalysisAgent()
            except Exception as e:
                logger.warning(
                    "conversation_aware_classifier_init_failed",
                    error=str(e),
                    fallback="pattern_based",
                )

        # Pattern definitions for fallback classification
        self.patterns = self._initialize_patterns()

        # Intent mappings
        self.workflow_mappings = {
            UserIntent.EMAIL_REQUEST: "email_workflow",
            UserIntent.OCM_COMMUNICATION: "ocm_communications",
            UserIntent.DOCUMENT_GENERATION: "document_generation",
            UserIntent.DATA_ANALYSIS: "data_analysis",
            UserIntent.CONTENT_CREATION: "content_creation",
            UserIntent.PROCESS_OPTIMIZATION: "process_optimization",
        }

        # Enterprise components
        try:
            privacy_logger = PrivacySafeLogger()
            self.audit_manager = EnterpriseAuditManager(privacy_logger=privacy_logger)
        except (ImportError, NameError):
            self.audit_manager = None

    def _create_default_llm(self) -> ChatOpenAI:
        """Create default LLM with proper authentication."""
        try:
            config = LLMConfig.from_env()
            return config.create_agent_llm()
        except (ImportError, ValueError, KeyError, AttributeError):
            # LLM configuration failed - use fallback configuration
            import os

            llm_kwargs = {
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "max_tokens": 200,
                "timeout": 10.0,
            }

            if os.getenv("OPENAI_ORGANIZATION"):
                llm_kwargs["organization"] = os.getenv("OPENAI_ORGANIZATION")

            return ChatOpenAI(**llm_kwargs)

    def _initialize_patterns(self) -> dict[UserIntent, list[str]]:
        """Initialize regex patterns for fallback classification."""
        return {
            UserIntent.EMAIL_REQUEST: [
                r"\\b(?:email|e-mail|mail|message|send|draft|write|compose)\\b.*\\b(?:to|for|about|regarding)\\b",
                r"\\b(?:email|e-mail|mail)\\b.*\\b(?:help|assist|support)\\b",
                r"\\b(?:draft|write|compose|create)\\b.*\\b(?:email|e-mail|mail|message)\\b",
                r"\\b(?:need|want|looking)\\b.*\\b(?:email|e-mail|mail)\\b",
            ],
            UserIntent.HELP_REQUEST: [
                r"\\b(?:help|assist|support|guidance|aid)\\b",
                r"\\b(?:what can|how can|can you)\\b",
                r"\\b(?:capabilities|features|functions|options)\\b",
                r"\\b(?:explain|show|tell)\\b.*\\b(?:how|what)\\b",
            ],
            UserIntent.GREETING: [
                r"^(?:hi|hello|hey|good morning|good afternoon|good evening|greetings?)\\b",
                r"\\b(?:how are you|how's it going|what's up)\\b",
            ],
            UserIntent.OCM_COMMUNICATION: [
                r"\\b(?:change management|organizational change|change communication)\\b",
                r"\\b(?:announce|announcement|communicate change|inform about)\\b",
                r"\\b(?:stakeholder|employee|team)\\b.*\\b(?:communication|update|message)\\b",
            ],
            UserIntent.DOCUMENT_GENERATION: [
                r"\\b(?:create|generate|write|draft)\\b.*\\b(?:document|report|proposal|presentation)\\b",
                r"\\b(?:document|report|proposal|presentation)\\b.*\\b(?:help|create|generate)\\b",
            ],
            UserIntent.DATA_ANALYSIS: [
                r"\\b(?:analyze|analysis|data|insights|report|dashboard)\\b",
                r"\\b(?:data|analytics|metrics|statistics)\\b.*\\b(?:help|analyze|create)\\b",
            ],
            UserIntent.CONTENT_CREATION: [
                r"\\b(?:content|blog|post|article|marketing)\\b.*\\b(?:create|write|generate)\\b",
                r"\\b(?:social media|marketing|campaign)\\b.*\\b(?:content|post)\\b",
            ],
            UserIntent.PROCESS_OPTIMIZATION: [
                r"\\b(?:process|workflow|optimize|improve|efficiency)\\b",
                r"\\b(?:automation|streamline|enhance)\\b.*\\b(?:process|workflow)\\b",
            ],
        }

    def _get_session_id_safely(
        self, state: UniversalWorkflowState | dict[str, Any] | None
    ) -> str:
        """Safely extract session ID using defensive programming."""
        if state is None:
            return "unknown"

        try:
            match state:
                case _ if hasattr(state, "session_id"):
                    return state.session_id or "unknown"
                case dict():
                    return state.get("session_id", "unknown")
                case _:
                    return "unknown"
        except AttributeError:
            if isinstance(state, dict):
                return state.get("session_id", "unknown")
            return "unknown"

    def _validate_inputs(self, user_input: str) -> None:
        """Validate inputs with comprehensive error collection."""
        errors = []

        if not user_input:
            errors.append(ValueError("user_input cannot be empty"))

        if not isinstance(user_input, str):
            errors.append(TypeError(f"user_input must be str, got {type(user_input)}"))

        if len(user_input) > 10000:
            errors.append(ValueError(f"user_input too long: {len(user_input)} chars"))

        if errors:
            raise ExceptionGroup("Input validation failed", errors)

    async def _classify_with_conversation_context(
        self,
        user_input: str,
        state: UniversalWorkflowState | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Classify using conversation-aware agent."""
        if not self.conversation_aware_classifier or not state:
            return None

        try:
            result = await self.conversation_aware_classifier.execute(
                user_input, state, timeout=10.0, max_retries=2
            )

            if result and result.get("confidence", 0) > 0.7:
                # Map conversation intent to UserIntent
                intent_str = result.get("intent", "general_conversation")
                mapped_intent = self._map_conversation_intent_to_user_intent(intent_str)

                logger.info(
                    "conversation_aware_classification_success",
                    user_input=user_input[:50],
                    conversation_intent=intent_str,
                    mapped_intent=mapped_intent.value,
                    confidence=result.get("confidence", 0),
                )

                return {
                    "intent": mapped_intent,
                    "confidence": result.get("confidence", 0),
                    "method": "conversation_aware",
                    "conversation_context": True,
                }

        except Exception as e:
            logger.warning(
                "conversation_aware_classification_failed",
                error=str(e),
                fallback="structured_llm",
            )

        return None

    def _map_conversation_intent_to_user_intent(self, intent_str: str) -> UserIntent:
        """Map conversation-aware intent categories to UserIntent enum."""
        intent_mapping = {
            "user_question": UserIntent.HELP_REQUEST,
            "user_request": UserIntent.EMAIL_REQUEST,
            "user_complaint": UserIntent.HELP_REQUEST,
            "user_praise": UserIntent.HELP_REQUEST,
            "general_conversation": UserIntent.GREETING,
            "escalation_request": UserIntent.HELP_REQUEST,
            "task_completion": UserIntent.HELP_REQUEST,
        }
        return intent_mapping.get(intent_str, UserIntent.UNCLEAR)

    async def _classify_with_structured_llm(
        self, user_input: str
    ) -> IntentClassificationResult | None:
        """Use LangChain structured output for intent classification."""
        try:
            structured_llm = self.llm.with_structured_output(IntentClassificationResult)
        except Exception as e:
            logger.warning("structured_output_failed", error=str(e))
            return None

        system_prompt = """You are an expert intent classifier for a business communication assistant.

Classify user input into one of these specific intents:

- EMAIL_REQUEST: User wants help with email communication, writing, drafting, or sending emails
- HELP_REQUEST: User asking for help, capabilities, or what the assistant can do
- GREETING: Simple greetings like hello, hi, good morning, how are you
- OCM_COMMUNICATION: Change management, organizational communications, announcements
- DOCUMENT_GENERATION: Creating documents, reports, proposals, presentations
- DATA_ANALYSIS: Analyzing data, generating insights, reports, dashboards
- CONTENT_CREATION: Creating marketing content, blogs, social media posts
- PROCESS_OPTIMIZATION: Improving workflows, processes, efficiency, automation
- UNCLEAR: Cannot determine clear intent, ambiguous request needing clarification
- INVALID: Very short, incomplete, nonsensical, or inappropriate input

Be precise and confident in your classification. Consider the primary intent."""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "Classify this user input: {user_input}"),
            ]
        )

        try:
            classification_chain = prompt | structured_llm
            result = await classification_chain.ainvoke(
                {"user_input": user_input}, config={"timeout": 10}
            )

            if (
                result
                and hasattr(result, "intent")
                and hasattr(result, "confidence")
                and result.confidence > 0.7
            ):
                logger.info(
                    "llm_classification_success",
                    user_input=user_input[:50],
                    intent=result.intent.value,
                    confidence=result.confidence,
                )
                return result

        except Exception as e:
            logger.warning("llm_classification_failed", error=str(e))

        return None

    def _classify_with_patterns(self, user_input: str) -> UserIntent:
        """Fallback pattern-based classification."""
        user_lower = user_input.lower().strip()

        # Check email patterns first
        for intent, patterns in self.patterns.items():
            if intent == UserIntent.EMAIL_REQUEST:
                for pattern in patterns:
                    if re.search(pattern, user_lower, re.IGNORECASE):
                        return UserIntent.EMAIL_REQUEST

        # Check other patterns using modern match/case
        for intent, patterns in self.patterns.items():
            if intent == UserIntent.EMAIL_REQUEST:
                continue

            for pattern in patterns:
                if re.search(pattern, user_lower, re.IGNORECASE):
                    return intent

        # Default classification
        match len(user_lower):
            case n if n < 3:
                return UserIntent.INVALID
            case _:
                return UserIntent.UNCLEAR

    @traceable(name="intent_classification")
    async def execute(
        self,
        user_input: str,
        state: UniversalWorkflowState | dict[str, Any] | None = None,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Execute multi-tier intent classification.

        LangGraph-aligned: Single responsibility execution.

        Args:
            user_input: User input to classify
            state: Optional workflow state for conversation context
            timeout: Maximum time to wait for classification
            max_retries: Maximum retry attempts

        Returns:
            Dict with comprehensive classification results
        """
        start_time = time.perf_counter()
        session_id = self._get_session_id_safely(state)

        logger.info(
            "intent_classification_started",
            message_length=len(user_input),
            has_state=state is not None,
            timeout=timeout,
        )

        # Input validation
        self._validate_inputs(user_input)

        try:
            async with asyncio.timeout(timeout):
                # Level 1: Conversation-aware classification
                if state:
                    conv_result = await self._classify_with_conversation_context(
                        user_input, state
                    )
                    if conv_result:
                        execution_time_ms = (time.perf_counter() - start_time) * 1000
                        return {
                            **conv_result,
                            "execution_time_ms": execution_time_ms,
                            "session_id": session_id,
                        }

                # Level 2: LLM structured output
                llm_result = await self._classify_with_structured_llm(user_input)
                if llm_result and llm_result.confidence > 0.7:
                    execution_time_ms = (time.perf_counter() - start_time) * 1000
                    return {
                        "intent": llm_result.intent,
                        "confidence": llm_result.confidence,
                        "method": "structured_llm",
                        "reasoning": llm_result.reasoning,
                        "execution_time_ms": execution_time_ms,
                        "session_id": session_id,
                    }

                # Level 3: Pattern fallback
                pattern_intent = self._classify_with_patterns(user_input)
                execution_time_ms = (time.perf_counter() - start_time) * 1000

                logger.info(
                    "pattern_classification_used",
                    intent=pattern_intent.value,
                    execution_time_ms=execution_time_ms,
                )

                return {
                    "intent": pattern_intent,
                    "confidence": 0.8,
                    "method": "pattern_based",
                    "execution_time_ms": execution_time_ms,
                    "session_id": session_id,
                }

        except TimeoutError:
            logger.error(
                "intent_classification_timeout",
                timeout=timeout,
                session_id=session_id,
            )
            return {
                "intent": UserIntent.UNCLEAR,
                "confidence": 0.3,
                "method": "timeout_fallback",
                "error": "Classification timed out",
                "session_id": session_id,
            }

        except Exception as e:
            logger.error(
                "intent_classification_error",
                error=str(e),
                session_id=session_id,
            )
            return {
                "intent": UserIntent.UNCLEAR,
                "confidence": 0.3,
                "method": "error_fallback",
                "error": str(e),
                "session_id": session_id,
            }

    def should_show_capabilities(self, intent: UserIntent) -> bool:
        """Determine if capabilities guidance should be shown."""
        return intent in [
            UserIntent.HELP_REQUEST,
            UserIntent.CAPABILITIES_INQUIRY,
            UserIntent.GREETING,
            UserIntent.UNCLEAR,
        ]

    def get_workflow_type(self, intent: UserIntent) -> str | None:
        """Map intent to appropriate workflow type."""
        return self.workflow_mappings.get(intent)

    async def get_complete_response(
        self,
        user_input: str,
        state: UniversalWorkflowState | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Get complete intent classification response with routing information.

        Args:
            user_input: User input to classify
            state: Optional workflow state

        Returns:
            Dict with classification and routing information
        """
        classification = await self.execute(user_input, state)
        intent = classification["intent"]

        # Build response based on intent type
        if self.should_show_capabilities(intent):
            return {
                "user_message": "I'd be happy to help! I can assist with email communications, document generation, data analysis, content creation, and process optimization. What would you like to work on?",
                "message_type": "help_response",
                "requires_input": False,
                "suggestions": [
                    "Create an email campaign",
                    "Generate a report",
                    "Analyze data",
                    "Write a document",
                ],
                **classification,
            }

        workflow_type = self.get_workflow_type(intent)
        if workflow_type:
            return {
                "message_type": "route_to_workflow",
                "workflow_type": workflow_type,
                "next_agent": "requirements_gathering_agent",
                "requires_input": True,
                "silent_handoff": True,
                **classification,
            }

        # Default unclear response
        return {
            "user_message": "I'd be happy to help! Could you tell me more about what you're looking to accomplish?",
            "message_type": "clarification_request",
            "requires_input": True,
            "suggestions": [
                "I need help with email communications",
                "I want to create a document",
                "Show me what you can do",
            ],
            **classification,
        }


# Quick utility function for async classification
async def classify_user_intent_async(
    user_input: str,
    state: UniversalWorkflowState | dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Quick utility function for async intent classification.

    Args:
        user_input: User input to classify
        state: Optional workflow state
        **kwargs: Additional parameters

    Returns:
        Dict with classification results
    """
    classifier = IntentClassifierAgent()
    return await classifier.execute(user_input, state, **kwargs)


# Backward compatibility
async def get_intent_response_async(
    user_input: str, state: UniversalWorkflowState | dict[str, Any] | None = None
) -> dict[str, Any]:
    """Get complete intent response with routing."""
    classifier = IntentClassifierAgent()
    return await classifier.get_complete_response(user_input, state)
