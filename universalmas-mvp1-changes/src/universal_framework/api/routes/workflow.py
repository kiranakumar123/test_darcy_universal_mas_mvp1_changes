"""Workflow execution endpoints."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from universal_framework.api.dependencies import (
    get_session_manager,
    get_session_storage,
)
from universal_framework.api.models.responses import (
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
)
from universal_framework.api.response_transformer import APIResponseTransformer

# Import modern node-based intent classifier
from universal_framework.nodes.agents.intent_classifier_agent import (
    get_intent_response_async,
)
from universal_framework.observability import UniversalFrameworkLogger

# Make agent execution logging optional
try:
    from universal_framework.observability.agent_execution_logger import (
        AgentExecutionLogger,
    )

    _agent_logging_available = True
except ImportError:
    _agent_logging_available = False

# Make OpenTelemetry tracing optional
try:
    from universal_framework.api.tracing import execute_workflow_with_tracing

    _tracing_available = True
except ImportError:
    _tracing_available = False

    # Fallback for when OpenTelemetry is not available
    async def execute_workflow_with_tracing(
        workflow: Any,
        initial_state: UniversalWorkflowState,
        session_id: str,
    ) -> UniversalWorkflowState:
        """Execute workflow without tracing (fallback)."""
        # Enhanced config following LangGraph best practices
        config = {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": "",  # Required for proper checkpointer operation
            },
            "recursion_limit": 200,  # Increased recursion limit to match graph configuration
        }
        return await workflow.ainvoke(initial_state, config=config)


# Import HumanMessage for creating user input messages
from langchain_core.messages import HumanMessage

from universal_framework.api.workflow_registry import workflow_registry
from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.redis.session_storage import SessionStorage
from universal_framework.security.session_validator import SessionValidator
from universal_framework.session.session_manager import EnterpriseSessionManager

router = APIRouter(prefix="/api/v1", tags=["workflow"])

_session_manager_dep = Depends(get_session_manager)
_session_storage_dep = Depends(get_session_storage)

session_validator = SessionValidator()
# PERFORMANCE OPTIMIZATION: Single consolidated logger
workflow_logger = UniversalFrameworkLogger("workflow_routes")


async def provide_capabilities_response(
    request: WorkflowExecuteRequest, session_storage: SessionStorage
) -> WorkflowExecuteResponse:
    """Provide direct capabilities response for help requests without entering workflow."""
    capabilities_message = """
🤖 **Universal Multi-Agent System - Available Capabilities**

**Organizational Change Management (OCM):**
• Strategic change analysis and planning
• Stakeholder impact assessment
• Communication plan development
• Risk mitigation strategies
• Implementation roadmaps

**Document Generation:**
• Technical documentation
• Business process documentation
• Training materials
• Compliance reports
• Strategic presentations

**Data Analysis & Insights:**
• Performance metrics analysis
• Trend identification
• Risk assessment
• Recommendation engines
• Impact analysis

**Available Commands:**
• `/help` - Show this capabilities overview
• `/start [workflow_type]` - Begin specific workflow
• `/status` - Check current session status
• `/reset` - Reset current session

**Example Usage:**
"Generate a change management strategy for implementing new CRM system"
"Create technical documentation for our API integration"
"Analyze quarterly performance data and provide insights"

How can I assist you today?
"""

    session_id = request.session_id or f"help_{uuid4().hex[:8]}"

    return WorkflowExecuteResponse(
        session_id=session_id,
        response=capabilities_message,
        timestamp=datetime.now().isoformat(),  # Use ISO string for JSON compatibility
        workflow_phase="completed",
        completion_percentage=100.0,
        deliverables={
            "type": "capabilities_response",
            "intent": "help_request",
            "source": "help_system",
        },
        execution_mode="direct_response",
        # Note: Backend-only fields (execution_time_seconds, success, status, task_id) logged internally but not sent to frontend
    )


@router.post("/workflow/execute", response_model=WorkflowExecuteResponse)
async def execute_workflow_hybrid(
    request: WorkflowExecuteRequest,
    background_tasks: BackgroundTasks,
    session_manager: EnterpriseSessionManager = _session_manager_dep,
    session_storage: SessionStorage = _session_storage_dep,
) -> WorkflowExecuteResponse:
    try:
        execution_start = datetime.now()

        # 🎯 INTENT CLASSIFICATION: Check user intent before routing to workflow
        if request.message:
            intent_start_time = time.perf_counter()

            # Get current session state for phase-aware intent classification
            current_state = None

            # Generate session ID if not provided (new session)
            effective_session_id = request.session_id or str(uuid4())

            # PRIORITY 1: Check if session configuration is provided in request context
            if request.context and "session_config" in request.context:
                session_config = request.context["session_config"]
                current_state = {
                    "workflow_phase": session_config.get("workflow_phase"),
                    "user_id": session_config.get(
                        "user_id", request.context.get("user_id")
                    ),
                    "context": session_config.get("context", {}),
                    "session_id": session_config.get(
                        "session_id", effective_session_id
                    ),
                }

                # DEBUG: Log inline session config usage

                debug_logger = workflow_logger
                debug_logger.info(
                    "using_inline_session_config",
                    session_id=(current_state.get("session_id") or "unknown")[:8] + "...",
                    workflow_phase=current_state.get("workflow_phase", "not_set"),
                    source="request_context",
                )

                # Optionally store this session state for future use
                if effective_session_id and current_state.get("workflow_phase"):
                    try:
                        await session_manager.store_session_state(
                            effective_session_id, current_state
                        )
                        debug_logger.info(
                            "stored_inline_session_config",
                            session_id=(effective_session_id or "unknown")[:8] + "...",
                        )
                    except Exception as e:
                        debug_logger.warning(
                            "failed_to_store_inline_session_config",
                            error=str(e),
                            session_id=(effective_session_id or "unknown")[:8] + "...",
                        )

            # PRIORITY 2: Try to get existing session state from session manager (if session exists)
            elif request.session_id:
                try:
                    current_state = await session_manager.get_session_state(
                        request.session_id
                    )

                    # DEBUG: Log session state retrieval details

                    debug_logger = workflow_logger
                    debug_logger.info(
                        "session_state_retrieved",
                        session_id=(request.session_id or "unknown")[:8] + "...",
                        state_exists=current_state is not None,
                        state_type=(
                            type(current_state).__name__ if current_state else "None"
                        ),
                        workflow_phase=(
                            getattr(
                                current_state,
                                "workflow_phase",
                                (
                                    current_state.get("workflow_phase")
                                    if isinstance(current_state, dict)
                                    else "not_found"
                                ),
                            )
                            if current_state
                            else "no_state"
                        ),
                        source="session_manager",
                    )
                except Exception as e:
                    # If session state retrieval fails, continue with stateless classification
                    current_state = None

                    debug_logger = workflow_logger
                    debug_logger.warning(
                        "session_state_retrieval_failed",
                        session_id=(request.session_id or "unknown")[:8] + "...",
                        error=str(e),
                    )

            # PRIORITY 3: Initialize new session state for conversation-aware classification
            if current_state is None:
                # Create initial session state for new sessions
                current_state = {
                    "workflow_phase": "INITIALIZATION",
                    "user_id": None,
                    "session_id": effective_session_id,
                    "context": {},
                    "messages": [],
                }

                # DEBUG: Log new session initialization

                debug_logger = workflow_logger
                debug_logger.info(
                    "new_session_initialized",
                    session_id=(effective_session_id or "unknown")[:8] + "...",
                    workflow_phase="INITIALIZATION",
                    source="new_session_creation",
                )

            # Use state-aware intent classification if we have session state
            # Build complete conversation context for intent classification
            conversation_state = None
            if current_state is not None:
                # Import required for message creation
                from langchain_core.messages import HumanMessage

                # Create a conversation context for intent classification
                conversation_state = {
                    "workflow_phase": (
                        current_state.get("workflow_phase")
                        if isinstance(current_state, dict)
                        else getattr(current_state, "workflow_phase", None)
                    ),
                    "user_id": (
                        current_state.get("user_id")
                        if isinstance(current_state, dict)
                        else getattr(current_state, "user_id", None)
                    ),
                    "session_id": (
                        current_state.get("session_id")
                        if isinstance(current_state, dict)
                        else getattr(current_state, "session_id", None)
                    ),
                    "context": (
                        current_state.get("context")
                        if isinstance(current_state, dict)
                        else getattr(current_state, "context_data", {})
                    ),
                    "messages": [],
                }

                # Add existing conversation history if available
                if isinstance(current_state, dict):
                    existing_messages = current_state.get("messages", [])
                elif hasattr(current_state, "messages"):
                    existing_messages = current_state.messages
                else:
                    existing_messages = []

                # Copy existing messages
                conversation_state["messages"] = (
                    existing_messages.copy() if existing_messages else []
                )

                # Add current user message to conversation context
                conversation_state["messages"].append(
                    HumanMessage(content=request.message)
                )

                # DEBUG: Log conversation context construction

                debug_logger = workflow_logger
                debug_logger.info(
                    "conversation_context_built",
                    session_id=(effective_session_id or "unknown")[:8] + "...",
                    messages_count=len(conversation_state["messages"]),
                    has_history=len(conversation_state["messages"]) > 1,
                    workflow_phase=conversation_state.get("workflow_phase", "not_set"),
                )

            intent_response = await get_intent_response_async(
                request.message, conversation_state
            )
            intent_execution_time_ms = (time.perf_counter() - intent_start_time) * 1000

            # DEBUG: Log intent classification results

            debug_logger = workflow_logger
            debug_logger.info(
                "intent_classification_completed",
                session_id=(effective_session_id or "unknown")[:8] + "...",
                message_type=intent_response.get("message_type", "unknown"),
                current_phase=intent_response.get("current_phase", "not_set"),
                state_was_passed=current_state is not None,
                classified_intent=intent_response.get("classified_intent", "unknown"),
            )

            # Comprehensive agent logging
            if _agent_logging_available:
                try:
                    execution_logger = AgentExecutionLogger()
                    execution_logger.log_agent_execution(
                        session_id=request.session_id or str(uuid4()),
                        agent_name="intent_classifier",
                        agent_response=intent_response,
                        rationale=f"Classified user message '{request.message}' and determined appropriate response type: {intent_response.get('message_type', 'unknown')}",
                        prompt_template="Intent classification using rule-based patterns and help detection logic",
                        input_data={
                            "user_message": request.message,
                            "message_length": len(request.message),
                            "workflow_id": getattr(request, "workflow_id", None),
                            "use_case": getattr(request, "use_case", None),
                            "execution_time_ms": intent_execution_time_ms,
                            "message_type_detected": intent_response.get(
                                "message_type", "unknown"
                            ),
                            "help_response": intent_response.get("message_type")
                            == "help_response",
                        },
                        execution_time_ms=intent_execution_time_ms,
                        workflow_phase=intent_response.get(
                            "current_phase", "INITIALIZATION"
                        ),
                    )
                except Exception as e:
                    # Log the error but don't break the workflow

                    logger = workflow_logger
                    # Compute session_id defensively to avoid KeyError in logger
                    sid = request.session_id if getattr(request, "session_id", None) else "unknown"
                    logger.warning(
                        "agent_execution_logging_failed",
                        error=str(e),
                        session_id=sid,
                    )

            # If this is a help request, provide immediate response
            if intent_response.get("message_type") in [
                "help_response",
                "phase_specific_help",
            ]:
                # Log internal execution for debugging (existing)
                execution_time_ms = (
                    datetime.now() - execution_start
                ).total_seconds() * 1000
                APIResponseTransformer.log_internal_execution(
                    agent_response=intent_response,
                    session_id=request.session_id or str(uuid4()),
                    execution_time_ms=execution_time_ms,
                    agent_name="intent_classifier",
                )

                # Return clean frontend response
                frontend_response = APIResponseTransformer.transform_to_frontend(
                    session_id=request.session_id or str(uuid4()),
                    agent_response={**intent_response, "source": "intent_classifier"},
                )

                # Log internal execution details for debugging
                APIResponseTransformer.log_internal_execution(
                    agent_response=intent_response,
                    session_id=request.session_id or str(uuid4()),
                    execution_time_ms=execution_time_ms,
                    agent_name="intent_classifier",
                )

                # Return response using ONLY frontend fields (no backend metadata)
                # Fix workflow_phase to use valid enum value
                current_phase = intent_response.get("current_phase", "INITIALIZATION")
                if current_phase == "not_set" or current_phase not in [
                    phase.value for phase in WorkflowPhase
                ]:
                    current_phase = "INITIALIZATION"

                try:
                    response_obj = WorkflowExecuteResponse(
                        session_id=frontend_response["session_id"],
                        response=frontend_response["message"],
                        timestamp=datetime.now().isoformat(),  # Use ISO string for JSON compatibility
                        workflow_phase=current_phase,
                        completion_percentage=frontend_response.get(
                            "completion_percentage", 100.0
                        ),  # Defensive access with help request default
                        deliverables={
                            "source": frontend_response["source"],
                            "message_type": frontend_response["message_type"],
                        },
                        execution_mode="sync",
                        # Note: Removed status, execution_time_seconds, success, task_id per user request
                    )
                except Exception as e:
                    # Log the exact serialization error for debugging
                    sid = request.session_id if getattr(request, "session_id", None) else "unknown"
                    workflow_logger.error(
                        "response_serialization_error",
                        error=str(e),
                        frontend_response_keys=list(frontend_response.keys()),
                        current_phase=current_phase,
                        session_id=sid,
                    )
                    # Re-raise to trigger global exception handler
                    raise HTTPException(
                        status_code=500,
                        detail=f"Response serialization failed: {str(e)}",
                    ) from e

                # DEBUG: Monitor response size
                import json

                debug_logger = workflow_logger
                try:
                    # Convert to dict and handle datetime serialization
                    response_dict = response_obj.model_dump()
                    # Convert datetime to ISO string for JSON serialization
                    if "timestamp" in response_dict and hasattr(
                        response_dict["timestamp"], "isoformat"
                    ):
                        response_dict["timestamp"] = response_dict[
                            "timestamp"
                        ].isoformat()

                    response_size = len(json.dumps(response_dict, default=str))
                    debug_logger.info(
                        "help_response_size",
                        session_id=(frontend_response.get("session_id") or "unknown")[:8] + "...",
                        response_size_bytes=response_size,
                        message_length=len(frontend_response["message"]),
                        message_type=frontend_response["message_type"],
                    )
                except Exception as e:
                    debug_logger.warning(
                        "response_size_calculation_failed",
                        error=str(e),
                        session_id=(frontend_response.get("session_id") or "unknown")[:8] + "...",
                    )

                return response_obj

            # If this is an email request, silent handoff to requirements gathering agent
            elif intent_response.get("message_type") == "route_to_workflow":
                # Log silent handoff
                execution_time_ms = (
                    datetime.now() - execution_start
                ).total_seconds() * 1000
                APIResponseTransformer.log_internal_execution(
                    agent_response=intent_response,
                    session_id=request.session_id or str(uuid4()),
                    execution_time_ms=execution_time_ms,
                    agent_name="intent_classifier",
                )

                # Override workflow type for email workflow
                request.workflow_type = "email_workflow"
                if hasattr(request, "use_case"):
                    request.use_case = "email_composition"

                # Store intent context in session for requirements agent
                session_id = request.session_id or str(uuid4())
                try:
                    # Check if store_session_data method exists (defensive programming)
                    if hasattr(session_storage, "store_session_data"):
                        await session_storage.store_session_data(
                            session_id,
                            "intent_context",
                            intent_response.get("extracted_context", {}),
                        )
                        await session_storage.store_session_data(
                            session_id,
                            "classified_intent",
                            intent_response.get("classified_intent", "email_request"),
                        )
                        await session_storage.store_session_data(
                            session_id,
                            "handoff_data",
                            intent_response.get("handoff_data", {}),
                        )
                    else:
                        # Log warning if method doesn't exist

                        logger = workflow_logger
                        logger.warning(
                            "store_session_data_method_not_available",
                            session_id=(session_id or "unknown"),
                        )
                except Exception as e:
                    # Log warning but continue - requirements agent can work without context

                    logger = workflow_logger
                    logger.warning(
                        "intent_context_storage_failed",
                        error=str(e),
                        session_id=(session_id or "unknown"),
                    )

                # Implement LangGraph conditional routing pattern for silent handoff
                handoff_data = intent_response.get("handoff_data", {})
                context_analysis = handoff_data.get("context_sufficiency_analysis", {})

                # Check if context is sufficient to skip requirements collection
                if context_analysis.get("ready_for_strategy_agent", False):
                    # Context is sufficient - route directly to strategy generation
                    # This follows the LangGraph conditional routing standard

                    logger = workflow_logger
                    logger.info(
                        "silent_handoff_direct_routing",
                        session_id=(session_id or "unknown"),
                        next_agent="strategy_generator",
                        reason="context_sufficient",
                        recipient_confidence=context_analysis.get(
                            "recipient_confidence", 0
                        ),
                        purpose_confidence=context_analysis.get(
                            "purpose_confidence", 0
                        ),
                    )

                    # Execute strategy generator directly via LangGraph workflow
                    workflow = workflow_registry.get_workflow(
                        "email_workflow", session_storage=session_storage
                    )

                    # Create initial state for strategy generation
                    initial_state = create_initial_state(request)

                    # Execute the workflow with the specific strategy_generator node
                    try:
                        result_state = await execute_workflow_with_tracing(
                            workflow, initial_state, session_id
                        )

                        # Extract strategy from result
                        strategy = (
                            result_state.email_strategy
                            if hasattr(result_state, "email_strategy")
                            else result_state.get("email_strategy")
                        )

                        if strategy:
                            response_message = f"I've analyzed your request and created a strategy for your {strategy.email_type} email. The approach will be {strategy.overall_approach} with a {strategy.tone} tone."
                            completion = 60.0
                        else:
                            response_message = "I've processed your request and am preparing your email strategy."
                            completion = 40.0

                        return WorkflowExecuteResponse(
                            session_id=session_id,
                            response=response_message,
                            timestamp=datetime.now().isoformat(),  # Use ISO string for JSON compatibility
                            workflow_phase="strategy_generation",
                            completion_percentage=completion,
                            deliverables={
                                "source": "strategy_generator",
                                "strategy": strategy.model_dump() if strategy else None,
                            },
                            execution_mode="async",
                        )

                    except Exception as exc:
                        sid = (frontend_response.get("session_id") or "unknown")
                        debug_logger.warning(
                            "response_size_calculation_failed",
                            error=str(exc),
                            session_id=(sid[:8] + "...") if isinstance(sid, str) else "unknown",
                        )
                        return WorkflowExecuteResponse(
                            session_id=session_id,
                            response="I encountered an issue while generating your strategy. Let me help you with the information I have.",
                            timestamp=datetime.now().isoformat(),  # Use ISO string for JSON compatibility
                            workflow_phase="strategy_generation",
                            completion_percentage=20.0,
                            deliverables={
                                "source": "strategy_generator",
                                "error": str(exc),
                            },
                            execution_mode="async",
                        )
                else:
                    # Context insufficient - proceed with standard workflow to collect requirements

                    logger = workflow_logger
                    logger.info(
                        "silent_handoff_requirements_needed",
                        session_id=(session_id or "unknown"),
                        next_agent="requirements_collector",
                        reason="context_insufficient",
                        missing_fields=context_analysis.get("missing_fields", []),
                    )
                    # Continue to standard workflow execution below

        # Continue with normal workflow execution for task requests or insufficient context

        # Continue with normal workflow execution for task requests
        workflow = workflow_registry.get_workflow(
            request.workflow_type, session_storage=session_storage
        )
        estimated_time = estimate_execution_time(
            request.workflow_type, request.target_deliverables or []
        )
        if estimated_time <= 30.0:
            return await execute_sync_workflow(
                workflow, request, session_manager, session_storage
            )
        return await execute_async_workflow(
            workflow,
            request,
            session_manager,
            background_tasks,
            session_storage,
        )
    except (ImportError, ModuleNotFoundError, AttributeError) as exc:
        # Only catch specific import/attribute errors, not response serialization issues
        raise HTTPException(
            status_code=500, detail=f"Workflow execution failed: {str(exc)}"
        ) from exc


async def execute_sync_workflow(
    workflow: Any,
    request: WorkflowExecuteRequest,
    session_manager: EnterpriseSessionManager,
    session_storage: SessionStorage,
) -> WorkflowExecuteResponse:
    initial_state = create_initial_state(request)
    # Defensive programming for LangGraph state conversion
    session_id = (
        initial_state.session_id
        if hasattr(initial_state, "session_id")
        else initial_state.get("session_id", "unknown")
    )
    user_id = (
        initial_state.user_id
        if hasattr(initial_state, "user_id")
        else initial_state.get("user_id", "unknown")
    )

    if not request.session_id:
        created = await session_storage.create_session(
            session_id,
            user_id,
            {
                "workflow_type": request.workflow_type,
                "execution_mode": "sync",
            },
        )
        if not created:
            raise HTTPException(status_code=500, detail="Session creation failed")
        workflow_logger.info(
            "session_created", session_id=session_id[:8] + "...", user_id=user_id
        )
    else:
        if not await session_storage.session_exists(session_id):
            workflow_logger.error("session_id_invalid", session_prefix=session_id[:8])
            raise HTTPException(status_code=404, detail="Session not found")
        workflow_logger.info(
            "session_retrieved", session_id=session_id[:8] + "...", user_id=user_id
        )
    start_time = datetime.now()
    result_state = await asyncio.wait_for(
        execute_workflow_with_tracing(workflow, initial_state, session_id),
        timeout=30.0,
    )
    exec_time = (datetime.now() - start_time).total_seconds()
    await session_manager.store_session_state(session_id, result_state)
    workflow_logger.info(
        "session_propagated",
        session_id=session_id[:8] + "...",
        user_id="user",
        direction="backend_to_frontend",
        endpoint="execute_sync_workflow",
    )
    # Log backend execution details
    # Log completion using the proper SessionFlowLogger method

    completion_logger = workflow_logger
    completion_logger.info(
        "sync_workflow_completed",
        execution_time_seconds=exec_time,
        session_id=session_id,
        success=True,
    )

    # Extract user message from the final state messages
    def extract_final_user_message(result_state) -> str:
        """Extract the user-facing response message from final workflow state."""
        try:
            # Get messages defensively (LangGraph compatibility)
            if hasattr(result_state, "messages"):
                messages = result_state.messages
            else:
                messages = result_state.get("messages", [])

            # Find the last agent message for user
            if messages:
                for message in reversed(messages):
                    if isinstance(message, dict):
                        # Check for user-facing content
                        user_msg = (
                            message.get("user_message")
                            or message.get("content")
                            or message.get("message")
                            or message.get("response_text")
                        )
                        if user_msg and isinstance(user_msg, str) and user_msg.strip():
                            return user_msg.strip()

            # Fallback: check context_data for latest response
            if hasattr(result_state, "context_data"):
                context = result_state.context_data
            else:
                context = result_state.get("context_data", {})

            if context and isinstance(context, dict):
                response = (
                    context.get("latest_response")
                    or context.get("agent_response")
                    or context.get("user_message")
                )
                if response and isinstance(response, str) and response.strip():
                    return response.strip()

            # Final fallback based on workflow phase
            if hasattr(result_state, "workflow_phase"):
                phase = result_state.workflow_phase
            else:
                phase = result_state.get("workflow_phase", "INITIALIZATION")

            match str(phase):
                case "INITIALIZATION":
                    return "I'd be happy to help! Could you tell me a bit more about what you're looking to accomplish? I can assist with change management communications, document generation, data analysis, and more."
                case _:
                    return "Thank you! I've processed your request. How else can I help you today?"

        except Exception as e:
            workflow_logger.warning(
                f"Failed to extract user message from final state: {e}"
            )
            return "I'm here to help! What would you like to work on today?"

    # Extract the actual user response instead of hardcoded "complete"
    user_response = extract_final_user_message(result_state)

    return WorkflowExecuteResponse(
        session_id=session_id,
        response=user_response,  # FIXED: Use extracted message instead of "complete"
        timestamp=datetime.now().isoformat(),  # Use ISO string for JSON compatibility
        workflow_phase=(
            result_state.workflow_phase
            if hasattr(result_state, "workflow_phase")
            else WorkflowPhase(
                result_state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
            )
        ),
        completion_percentage=(
            result_state.phase_completion.get(
                (
                    result_state.workflow_phase
                    if hasattr(result_state, "workflow_phase")
                    else WorkflowPhase(
                        result_state.get(
                            "workflow_phase", WorkflowPhase.INITIALIZATION.value
                        )
                    )
                ),
                0.0,
            )
            if hasattr(result_state, "phase_completion")
            else result_state.get("phase_completion", {}).get(
                (
                    result_state.workflow_phase
                    if hasattr(result_state, "workflow_phase")
                    else WorkflowPhase(
                        result_state.get(
                            "workflow_phase", WorkflowPhase.INITIALIZATION.value
                        )
                    )
                ),
                0.0,
            )
        ),
        deliverables={
            **(
                result_state.component_outputs
                if hasattr(result_state, "component_outputs")
                else result_state.get("component_outputs", {})
            ),
            "source": "workflow_engine",
        },
        execution_mode="sync",
        # Note: Backend-only fields (execution_time_seconds, success, status, task_id) logged internally but not sent to frontend
    )


async def execute_async_workflow(
    workflow: Any,
    request: WorkflowExecuteRequest,
    session_manager: EnterpriseSessionManager,
    background_tasks: BackgroundTasks,
    session_storage: SessionStorage,
) -> WorkflowExecuteResponse:
    task_id = f"task_{int(datetime.now().timestamp())}"
    background_tasks.add_task(
        execute_background_workflow,
        workflow,
        request,
        session_manager,
        task_id,
        session_storage,
    )
    session_id = request.session_id or str(uuid4())
    user_id = request.context.get("user_id", "user") if request.context else "user"
    if not request.session_id:
        created = await session_storage.create_session(
            session_id,
            user_id,
            {
                "workflow_type": request.workflow_type,
                "execution_mode": "async",
                "task_id": task_id,
            },
        )
        if not created:
            raise HTTPException(status_code=500, detail="Session creation failed")
        workflow_logger.info(
            "session_created", session_id=session_id[:8] + "...", user_id=user_id
        )
    else:
        if not await session_storage.session_exists(session_id):
            workflow_logger.error("session_id_invalid", session_prefix=session_id[:8])
            raise HTTPException(status_code=404, detail="Session not found")
        workflow_logger.info(
            "session_retrieved", session_id=session_id[:8] + "...", user_id=user_id
        )
    workflow_logger.info(
        "session_propagated",
        session_id=session_id[:8] + "...",
        user_id="user",
        direction="backend_to_frontend",
        endpoint="execute_async_workflow",
    )

    # Log backend execution details including task_id
    # Log async workflow queuing using proper structured logging

    async_logger = workflow_logger
    async_logger.info(
        "async_workflow_queued",
        task_id=task_id,
        session_id=session_id,
        queued_successfully=True,
    )

    return WorkflowExecuteResponse(
        session_id=session_id,
        response="queued",
        timestamp=datetime.now().isoformat(),  # Use ISO string for JSON compatibility
        workflow_phase="queued",
        completion_percentage=0.0,
        deliverables={
            "source": "workflow_engine",
            "task_info": "background_processing",
        },
        execution_mode="async",
        # Note: Backend-only fields (execution_time_seconds, success, status, task_id) logged internally but not sent to frontend
    )


async def execute_background_workflow(
    workflow: Any,
    request: WorkflowExecuteRequest,
    session_manager: EnterpriseSessionManager,
    task_id: str,
    session_storage: SessionStorage,
) -> None:
    initial_state = create_initial_state(request)
    # Defensive programming for LangGraph state conversion
    session_id = (
        initial_state.session_id
        if hasattr(initial_state, "session_id")
        else initial_state.get("session_id", "unknown")
    )
    user_id = (
        initial_state.user_id
        if hasattr(initial_state, "user_id")
        else initial_state.get("user_id", "unknown")
    )

    if not request.session_id:
        created = await session_storage.create_session(
            session_id,
            user_id,
            {
                "workflow_type": request.workflow_type,
                "execution_mode": "async",
                "task_id": task_id,
                "background": True,
            },
        )
        if not created:
            raise HTTPException(status_code=500, detail="Session creation failed")
        workflow_logger.info(
            "session_created", session_id=session_id[:8] + "...", user_id=user_id
        )
    else:
        if not await session_storage.session_exists(session_id):
            workflow_logger.error("session_id_invalid", session_prefix=session_id[:8])
            raise HTTPException(status_code=404, detail="Session not found")
        workflow_logger.info(
            "session_retrieved", session_id=session_id[:8] + "...", user_id=user_id
        )
    result_state = await execute_workflow_with_tracing(
        workflow, initial_state, session_id
    )
    await session_manager.store_session_state(session_id, result_state)
    await session_manager.store_session_state(task_id, result_state)
    workflow_logger.info(
        "session_propagated",
        session_id=session_id[:8] + "...",
        user_id="user",
        direction="backend_to_frontend",
        endpoint="execute_background_workflow",
    )


def estimate_execution_time(workflow_type: str, deliverables: list[str]) -> float:
    base_times = {
        "universal_general": 12.0,
        "ocm_communications": 15.0,
        "document_generation": 20.0,
        "data_analysis": 45.0,
        "content_creation": 10.0,
        "process_design": 25.0,
    }
    base_time = base_times.get(workflow_type, 20.0)
    return base_time + len(deliverables) * 5.0


def create_initial_state(request: WorkflowExecuteRequest) -> UniversalWorkflowState:
    session_id = request.session_id if request.session_id else str(uuid4())
    if not session_validator.validate_session_format(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    user_ctx = request.context or {}
    user_id = user_ctx.get("user_id", "user")

    # Create initial state with user message
    initial_state = UniversalWorkflowState(
        session_id=session_id,
        user_id=user_id,
        auth_token="token" * 3,
    )

    # Add the user's message as a HumanMessage to the state
    if request.message:
        user_message = HumanMessage(content=request.message)
        initial_state = initial_state.copy(
            update={
                "messages": [user_message],
                "context_data": {
                    "requested_deliverables": request.target_deliverables or []
                },
            }
        )
    else:
        initial_state = initial_state.copy(
            update={
                "context_data": {
                    "requested_deliverables": request.target_deliverables or []
                }
            }
        )

    return initial_state
