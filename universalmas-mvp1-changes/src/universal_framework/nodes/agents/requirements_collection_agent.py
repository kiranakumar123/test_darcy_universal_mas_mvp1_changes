"""Requirements collection agent using modern Python patterns."""

import time
from enum import Enum
from typing import Any

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool

from universal_framework.config.feature_flags import feature_flags
from universal_framework.contracts.messages import create_agent_message
from universal_framework.contracts.nodes import streamlined_node
from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.llm.providers import (
    LLMProvider,
    LLMProviderError,
    create_default_provider,
)
from universal_framework.llm.tools import RequirementsExtractionTool, StateAccessTool

from ...core.logging_foundation import get_safe_logger

# Removed direct imports - these will be imported conditionally when needed

# Make agent execution logging optional
try:
    from universal_framework.observability.agent_execution_logger import (
        AgentExecutionLogger,
    )

    _agent_logging_available = True
except ImportError:
    _agent_logging_available = False

logger = get_safe_logger(__name__)


class AgentExecutionStatus(Enum):
    """Agent execution status types."""

    COMPLETED = "completed"
    ERROR = "error"
    FALLBACK = "fallback"


class RequirementsCollectionAgent:
    """
    Real LangChain agent for collecting email requirements.

    LangGraph-aligned: Single responsibility node for requirements collection.
    The graph handles orchestration via conditional edges, not this node.
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        enterprise_config: Any | None = None,  # Use Any instead of conditional type
    ):
        self.llm_provider = llm_provider or create_default_provider()
        self.agent_executor: AgentExecutor | None = None
        self.enterprise_config = enterprise_config

        logger.info("requirements_agent_initialized")

    def _create_agent(self, state: UniversalWorkflowState) -> AgentExecutor:
        """Create LangChain agent with tools and prompt."""

        # Create tools
        tools: list[BaseTool] = [RequirementsExtractionTool(), StateAccessTool(state)]

        # Create custom prompt for requirements collection
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a requirements collection specialist for email generation.
Your job is to extract structured requirements from user requests about emails.

Always extract:
- audience: who will receive the email (internal_team, external_clients, executives, general)
- tone: desired communication style (professional, casual, formal)
- purpose: main goal (announcement, update, appreciation, inquiry)
- key_points: important messages to include

Use the requirements_extractor tool to analyze user input.
Provide clear, structured output that other agents can use.
""",
                ),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # Create agent with error handling
        try:
            llm = self.llm_provider.create_agent_llm()
            agent = create_openai_tools_agent(llm, tools, prompt)

            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=3,  # Prevent infinite loops
                max_execution_time=30.0,  # 30 second timeout
            )

            logger.info("agent_executor_created", tools_count=len(tools))
            return executor

        except LLMProviderError as e:
            e.add_note("Failed to create requirements collection agent")
            raise

    async def execute(self, state: UniversalWorkflowState) -> dict[str, Any]:
        """Execute requirements collection with enterprise LangSmith tracing."""

        start = time.perf_counter()
        session_id = getattr(state, "session_id", "unknown")

        # Check for intent context from silent handoff
        intent_context = self._get_intent_context(state)
        if intent_context:
            # Analyze if context is sufficient for email workflow
            context_analysis = self._analyze_email_context(intent_context)

            if context_analysis["sufficient"]:
                # Context is sufficient - pass to next agent
                logger.info(
                    "email_context_sufficient",
                    session_id=session_id,
                    context_analysis=context_analysis,
                )
                return self._create_sufficient_context_result(
                    intent_context, context_analysis
                )
            else:
                # Context insufficient - load email_requirements template
                logger.info(
                    "email_context_insufficient",
                    session_id=session_id,
                    context_analysis=context_analysis,
                )
                return await self._create_requirements_template_result(
                    intent_context, context_analysis
                )

        async def _run() -> dict[str, Any]:
            """Internal execution logic with enterprise tracing wrapper."""

            # Create agent executor if needed
            if self.agent_executor is None:
                try:
                    self.agent_executor = self._create_agent(state)
                except LLMProviderError as e:
                    logger.error("agent_creation_failed", error=str(e))

                    # Log agent failure
                    if _agent_logging_available:
                        try:
                            execution_logger = AgentExecutionLogger()
                            execution_logger.log_agent_execution(
                                session_id=session_id,
                                agent_name="requirements_collector",
                                agent_response={
                                    "error": "agent_creation_failed",
                                    "details": str(e),
                                },
                                rationale=f"Failed to create requirements collector agent: {str(e)}",
                                prompt_template="Agent initialization template",
                                input_data={
                                    "state_keys": (
                                        list(state.dict().keys())
                                        if hasattr(state, "dict")
                                        else []
                                    )
                                },
                                execution_time_ms=(time.perf_counter() - start) * 1000,
                                success=False,
                                error_message=str(e),
                                workflow_phase=getattr(
                                    state, "workflow_phase", "unknown"
                                ),
                            )
                        except Exception as log_error:
                            logger.warning(
                                "agent_execution_logging_failed", error=str(log_error)
                            )

                    return self._create_fallback_result(str(e))

            # Extract user input from messages
            user_input = self._extract_user_input(state.messages)
            if not user_input:
                logger.warning("no_user_input_found")

                # Log missing input
                if _agent_logging_available:
                    try:
                        execution_logger = AgentExecutionLogger()
                        execution_logger.log_agent_execution(
                            session_id=session_id,
                            agent_name="requirements_collector",
                            agent_response={
                                "error": "no_user_input",
                                "message_count": len(getattr(state, "messages", [])),
                            },
                            rationale="No user input found in state messages for requirements collection",
                            prompt_template="Requirements extraction from user messages",
                            input_data={
                                "message_count": len(getattr(state, "messages", []))
                            },
                            execution_time_ms=(time.perf_counter() - start) * 1000,
                            success=False,
                            error_message="No user input found in messages",
                            workflow_phase=getattr(state, "workflow_phase", "unknown"),
                        )
                    except Exception as log_error:
                        logger.warning(
                            "agent_execution_logging_failed", error=str(log_error)
                        )

                return self._create_error_result("No user input found in messages")

            # Execute agent with comprehensive error handling
            try:
                logger.info(
                    "executing_requirements_agent", input_length=len(user_input)
                )

                # Log agent execution start
                agent_start_time = time.perf_counter()

                result = await self.agent_executor.ainvoke(
                    {
                        "input": f"Extract email requirements from this request: {user_input}"
                    }
                )

                agent_execution_time_ms = (
                    time.perf_counter() - agent_start_time
                ) * 1000
                processed_result = self._process_agent_result(result, user_input)

                # Log successful execution
                if _agent_logging_available:
                    try:
                        execution_logger = AgentExecutionLogger()
                        execution_logger.log_agent_execution(
                            session_id=session_id,
                            agent_name="requirements_collector",
                            agent_response=processed_result,
                            rationale=f"Successfully collected requirements from user input: '{user_input[:100]}...' using LangChain agent executor",
                            prompt_template="Requirements extraction template with tools: RequirementsExtractionTool, StateAccessTool",
                            input_data={
                                "user_input": user_input,
                                "input_length": len(user_input),
                                "agent_tools": [
                                    "RequirementsExtractionTool",
                                    "StateAccessTool",
                                ],
                                "execution_time_ms": agent_execution_time_ms,
                                "output_keys": (
                                    list(processed_result.keys())
                                    if isinstance(processed_result, dict)
                                    else []
                                ),
                                "requirements_extracted": "requirements"
                                in str(processed_result).lower(),
                            },
                            execution_time_ms=agent_execution_time_ms,
                            success=True,
                            workflow_phase=getattr(state, "workflow_phase", "unknown"),
                        )
                    except Exception as log_error:
                        logger.warning(
                            "agent_execution_logging_failed", error=str(log_error)
                        )

                return processed_result

            except (TimeoutError, ConnectionError) as e:
                error_messages = [str(e)]
                logger.error(
                    "agent_execution_timeout_or_connection", errors=error_messages
                )

                # Log timeout/connection error
                if _agent_logging_available:
                    try:
                        execution_logger = AgentExecutionLogger()
                        execution_logger.log_agent_execution(
                            session_id=session_id,
                            agent_name="requirements_collector",
                            agent_response={
                                "error": "timeout_or_connection",
                                "details": error_messages,
                            },
                            rationale=f"Requirements collection failed due to timeout or connection error: {', '.join(error_messages)}",
                            prompt_template="Requirements extraction template with tools",
                            input_data={
                                "user_input": user_input,
                                "error_type": type(e).__name__,
                                "execution_time_ms": (time.perf_counter() - start)
                                * 1000,
                            },
                            execution_time_ms=(time.perf_counter() - start) * 1000,
                            success=False,
                            error_message=f"Timeout/Connection error: {', '.join(error_messages)}",
                            workflow_phase=getattr(state, "workflow_phase", "unknown"),
                        )
                    except Exception as log_error:
                        logger.warning(
                            "agent_execution_logging_failed", error=str(log_error)
                        )

                return self._create_fallback_result(
                    f"Agent execution failed: {', '.join(error_messages)}"
                )

            except Exception as e:
                e.add_note(
                    f"Requirements agent execution failed for input: {user_input[:50]}..."
                )
                logger.error(
                    "agent_execution_failed",
                    error=str(e),
                    input_preview=user_input[:50],
                )
                return self._create_fallback_result(str(e))

        # Conditional enterprise wrapper based on feature flags
        if feature_flags.is_enabled("LANGSMITH_TRACING") and self.enterprise_config:
            # Import only when needed to avoid safe mode bypass
            from ...observability import enhance_trace_real_agent_execution

            if enhance_trace_real_agent_execution:  # Check if not stubbed
                wrapped = enhance_trace_real_agent_execution(
                    "requirements_collector",
                    state.session_id,
                    self.enterprise_config,
                )(_run)
            else:
                wrapped = _run
        else:
            # Safe mode - no enterprise tracing
            wrapped = _run

        result = await wrapped()
        self._collect_performance_metrics(start, result)
        return result

    def _extract_user_input(self, messages: list[Any]) -> str:
        """Extract user input from messages."""
        for msg in reversed(messages):
            if msg.__class__.__name__ == "HumanMessage":
                return msg.content
        return ""

    def _process_agent_result(
        self, result: dict[str, Any], user_input: str
    ) -> dict[str, Any]:
        """Process agent output into structured result."""

        agent_output = result.get("output", "")

        # Parse requirements from agent output
        import json

        try:
            # Try to extract JSON from agent output
            match agent_output:
                case output if "{" in output:
                    json_start = output.find("{")
                    json_end = output.rfind("}") + 1
                    requirements_str = output[json_start:json_end]
                    requirements = json.loads(requirements_str)

                    logger.info(
                        "requirements_extracted_successfully",
                        audience=requirements.get("audience"),
                        tone=requirements.get("tone"),
                        purpose=requirements.get("purpose"),
                    )

                    return {
                        "status": AgentExecutionStatus.COMPLETED.value,
                        "requirements": requirements,
                        "confidence": 0.9,
                        "agent_output": agent_output,
                        "extraction_method": "agent_json",
                    }
                case _:
                    # Fallback to basic parsing
                    return self._create_basic_requirements(agent_output)

        except json.JSONDecodeError as e:
            logger.warning(
                "json_parse_failed", error=str(e), output_preview=agent_output[:100]
            )
            return self._create_basic_requirements(agent_output)

    def _create_basic_requirements(self, agent_output: str) -> dict[str, Any]:
        """Create basic requirements when JSON parsing fails."""
        requirements = {
            "audience": "professional",
            "tone": "professional",
            "purpose": "communication",
            "confidence": 0.6,
            "agent_analysis": agent_output,
            "key_points": [],
        }

        logger.info("basic_requirements_created", confidence=0.6)

        return {
            "status": AgentExecutionStatus.COMPLETED.value,
            "requirements": requirements,
            "confidence": 0.6,
            "agent_output": agent_output,
            "extraction_method": "basic_fallback",
        }

    def _create_error_result(self, error_message: str) -> dict[str, Any]:
        """Create error result."""
        return {"status": AgentExecutionStatus.ERROR.value, "error": error_message}

    def _create_fallback_result(self, error_message: str) -> dict[str, Any]:
        """Create fallback result with basic requirements."""
        return {
            "status": AgentExecutionStatus.FALLBACK.value,
            "error": error_message,
            "fallback_requirements": {
                "audience": "professional",
                "tone": "professional",
                "purpose": "communication",
            },
        }

    def _collect_performance_metrics(
        self, start: float, result: dict[str, Any]
    ) -> None:
        """Collect performance metrics following StrategyGenerator pattern."""

        total_duration = time.perf_counter() - start

        logger.info(
            "requirements_collection_performance",
            duration_ms=total_duration * 1000,
            extraction_method=result.get("extraction_method", "unknown"),
            requirements_count=len(
                result.get("requirements", {}).get("key_points", [])
            ),
        )

        # Performance warning if execution time exceeds threshold
        if total_duration > 0.5:
            logger.warning(
                "requirements_collection_performance_warning",
                duration_ms=total_duration * 1000,
                target_ms=500,
                exceeded_by_ms=(total_duration - 0.5) * 1000,
            )

    def _get_intent_context(
        self, state: UniversalWorkflowState
    ) -> dict[str, Any] | None:
        """Get intent context from silent handoff if available."""
        # Check for intent context in state
        intent_context = getattr(state, "intent_context", None)
        if intent_context:
            return intent_context

        # Check for intent context in context_data
        context_data = getattr(state, "context_data", {})
        if isinstance(context_data, dict):
            return context_data.get("intent_context")

        return None

    def _analyze_email_context(self, intent_context: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze email context to determine if sufficient for next agent.

        Criteria:
        - recipient: confidence >= 0.8
        - purpose: confidence >= 0.8
        """
        analysis = {
            "sufficient": False,
            "missing_fields": [],
            "recipient_analysis": {},
            "purpose_analysis": {},
            "recommendations": [],
        }

        # Analyze recipient
        recipient = intent_context.get("recipient", {})
        if isinstance(recipient, dict):
            recipient_value = recipient.get("value")
            recipient_confidence = recipient.get("confidence", 0.0)

            analysis["recipient_analysis"] = {
                "value": recipient_value,
                "confidence": recipient_confidence,
                "sufficient": recipient_value and recipient_confidence >= 0.8,
            }

            if not analysis["recipient_analysis"]["sufficient"]:
                analysis["missing_fields"].append("recipient")
                analysis["recommendations"].append("Ask for email recipient")
        else:
            analysis["recipient_analysis"] = {"sufficient": False}
            analysis["missing_fields"].append("recipient")
            analysis["recommendations"].append("Ask for email recipient")

        # Analyze purpose
        purpose = intent_context.get("purpose", {})
        if isinstance(purpose, dict):
            purpose_value = purpose.get("value")
            purpose_confidence = purpose.get("confidence", 0.0)

            analysis["purpose_analysis"] = {
                "value": purpose_value,
                "confidence": purpose_confidence,
                "sufficient": purpose_value and purpose_confidence >= 0.8,
            }

            if not analysis["purpose_analysis"]["sufficient"]:
                analysis["missing_fields"].append("purpose")
                analysis["recommendations"].append("Ask for email purpose/topic")
        else:
            analysis["purpose_analysis"] = {"sufficient": False}
            analysis["missing_fields"].append("purpose")
            analysis["recommendations"].append("Ask for email purpose/topic")

        # Determine overall sufficiency
        analysis["sufficient"] = analysis["recipient_analysis"].get(
            "sufficient", False
        ) and analysis["purpose_analysis"].get("sufficient", False)

        return analysis

    def _create_sufficient_context_result(
        self, intent_context: dict[str, Any], context_analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """Create result when context is sufficient - pass to next agent."""
        return {
            "status": AgentExecutionStatus.COMPLETED.value,
            "requirements": {
                "recipient": intent_context.get("recipient", {}).get("value", ""),
                "purpose": intent_context.get("purpose", {}).get("value", ""),
                "tone": intent_context.get("tone", {}).get("value", "professional"),
                "context_sufficient": True,
                "source": "intent_classifier_handoff",
            },
            "key_points": [
                f"Recipient: {intent_context.get('recipient', {}).get('value', '')}",
                f"Purpose: {intent_context.get('purpose', {}).get('value', '')}",
                f"Tone: {intent_context.get('tone', {}).get('value', 'professional')}",
            ],
            "extraction_method": "intent_context_analysis",
            "context_analysis": context_analysis,
            "intent_context": intent_context,
        }

    async def _create_requirements_template_result(
        self, intent_context: dict[str, Any], context_analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """Create result with email_requirements template when context insufficient."""
        try:
            # Load email_requirements.json template
            import json
            from pathlib import Path

            template_path = Path(
                "src/universal_framework/config/ux/ux_templates/email_requirements.json"
            )
            with open(template_path, encoding="utf-8") as f:
                email_requirements = json.load(f)

            # Customize template with existing context
            template_response = email_requirements.get(
                "user_facing_guidance",
                "Let me help you create an email. I need a bit more information to get started.",
            )

            # Add context-specific guidance
            missing_fields = context_analysis.get("missing_fields", [])
            if missing_fields:
                if "recipient" in missing_fields and "purpose" in missing_fields:
                    template_response += "\n\nSpecifically, I need to know:\n• Who will receive this email?\n• What's the main purpose or topic of your message?"
                elif "recipient" in missing_fields:
                    template_response += (
                        "\n\nSpecifically, I need to know: Who will receive this email?"
                    )
                elif "purpose" in missing_fields:
                    template_response += "\n\nSpecifically, I need to know: What's the main purpose or topic of your message?"

            return {
                "status": AgentExecutionStatus.COMPLETED.value,
                "requirements": {
                    "template_response": template_response,
                    "partial_context": intent_context,
                    "missing_fields": missing_fields,
                    "template_loaded": True,
                    "source": "email_requirements_template",
                },
                "key_points": [
                    "Email requirements template loaded",
                    f"Missing fields: {', '.join(missing_fields)}",
                    "Awaiting user input for complete context",
                ],
                "extraction_method": "email_requirements_template",
                "context_analysis": context_analysis,
                "intent_context": intent_context,
                "template_data": email_requirements,
            }

        except Exception as e:
            logger.error("email_requirements_template_load_failed", error=str(e))

            # Fallback to hardcoded message
            return {
                "status": AgentExecutionStatus.COMPLETED.value,
                "requirements": {
                    "template_response": "Let me help you create an email. I need to know:\n• Who will receive this email?\n• What's the main purpose or topic of your message?",
                    "partial_context": intent_context,
                    "missing_fields": context_analysis.get(
                        "missing_fields", ["recipient", "purpose"]
                    ),
                    "template_loaded": False,
                    "source": "fallback_email_requirements",
                },
                "key_points": [
                    "Fallback email requirements prompt",
                    "Template load failed - using hardcoded guidance",
                ],
                "extraction_method": "fallback_requirements",
                "context_analysis": context_analysis,
                "intent_context": intent_context,
                "error": str(e),
            }


# Integration with workflow using modern patterns and LangGraph alignment
@streamlined_node("real_requirements_collector", WorkflowPhase.BATCH_DISCOVERY)
async def real_requirements_collector(
    state: UniversalWorkflowState,
) -> UniversalWorkflowState:
    """
    Real LangChain agent with modern error handling.

    LangGraph-aligned: Single responsibility for requirements collection.
    State transformation only - orchestration handled by graph.
    """

    try:
        # Create and execute agent with optional default provider
        agent = RequirementsCollectionAgent()
        result = await agent.execute(state)

        # Process result based on status
        match result["status"]:
            case AgentExecutionStatus.COMPLETED.value:
                return _create_success_state(state, result)
            case AgentExecutionStatus.FALLBACK.value:
                return _create_fallback_state(state, result)
            case AgentExecutionStatus.ERROR.value | _:
                return _create_error_state(state, result)

    except (LLMProviderError, ConnectionError) as e:
        # Handle provider or connection errors gracefully
        logger.error("requirements_collection_failed", error=str(e))
        return _create_emergency_fallback_state(state, [str(e)])


def _create_success_state(
    state: UniversalWorkflowState, result: dict[str, Any]
) -> UniversalWorkflowState:
    """Create successful completion state."""

    response_message = create_agent_message(
        from_agent="real_requirements_collector",
        to_agent="email_workflow_orchestrator",
        content=f"Requirements collection {result['status']}",
        phase=WorkflowPhase.BATCH_DISCOVERY,
        data=result,
    )

    # Defensive programming for LangGraph state conversion
    try:
        current_phase_completion = state.phase_completion
    except AttributeError:
        current_phase_completion = (
            state.get("phase_completion", {}) if isinstance(state, dict) else {}
        )

    return state.copy(
        update={
            "workflow_phase": WorkflowPhase.BATCH_DISCOVERY,
            "phase_completion": {**current_phase_completion, "discovery": 0.9},
            "messages": [*state.messages, response_message],
            "context_data": {
                **state.context_data,
                "collected_requirements": result.get("requirements", {}),
                "requirements_confidence": result.get("confidence", 0.0),
                "last_active_agent": "real_requirements_collector",
                "agent_execution": {
                    "agent_type": "langchain_openai_tools",
                    "status": result["status"],
                },
            },
        }
    )


def _create_fallback_state(
    state: UniversalWorkflowState, result: dict[str, Any]
) -> UniversalWorkflowState:
    """Create fallback state with basic requirements."""

    response_message = create_agent_message(
        from_agent="real_requirements_collector",
        to_agent="email_workflow_orchestrator",
        content="Requirements collection failed, using fallback",
        phase=WorkflowPhase.BATCH_DISCOVERY,
        data=result,
    )

    # Defensive programming for LangGraph state conversion
    try:
        current_phase_completion = state.phase_completion
    except AttributeError:
        current_phase_completion = (
            state.get("phase_completion", {}) if isinstance(state, dict) else {}
        )

    return state.copy(
        update={
            "workflow_phase": WorkflowPhase.BATCH_DISCOVERY,
            "phase_completion": {**current_phase_completion, "discovery": 0.6},
            "messages": [*state.messages, response_message],
            "context_data": {
                **state.context_data,
                "collected_requirements": result.get("fallback_requirements", {}),
                "last_active_agent": "real_requirements_collector",
            },
        }
    )


def _create_error_state(
    state: UniversalWorkflowState, result: dict[str, Any]
) -> UniversalWorkflowState:
    """Create error state."""

    logger.error("requirements_agent_error", error=result.get("error"))
    return _create_fallback_state(state, result)


def _create_emergency_fallback_state(
    state: UniversalWorkflowState, error_messages: list[str]
) -> UniversalWorkflowState:
    """Create emergency fallback when all else fails."""

    fallback_requirements = {
        "audience": "professional",
        "tone": "professional",
        "purpose": "communication",
        "emergency_fallback": True,
        "errors": error_messages,
    }

    return state.copy(
        update={
            "context_data": {
                **state.context_data,
                "collected_requirements": fallback_requirements,
            }
        }
    )
