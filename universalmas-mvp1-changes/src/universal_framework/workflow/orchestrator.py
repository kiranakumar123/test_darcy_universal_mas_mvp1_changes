"""Email workflow orchestrator implementing LangGraph hierarchical patterns."""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from universal_framework.contracts.messages import (
    AgentMessage,
    create_agent_message,
    extract_agent_messages,
)
from universal_framework.contracts.nodes import streamlined_node
from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.observability import UniversalFrameworkLogger
from universal_framework.redis.session_storage import SessionStorage
from universal_framework.security.session_validator import (
    SessionSecurityError,
    SessionValidator,
)
from universal_framework.utils.session_logging import SessionFlowLogger
from universal_framework.workflow.routing import (
    EnhancedWorkflowRouter,
    RoutingDecision,
)

logger = UniversalFrameworkLogger("orchestrator")


def create_email_workflow_orchestrator(
    available_agents: list[str],
    session_storage: SessionStorage | None = None,
) -> Callable[[UniversalWorkflowState], Awaitable[UniversalWorkflowState]]:
    """Create workflow orchestrator for email coordination with enhanced error handling."""

    # Import dependencies - these should be available in the production environment

    router = EnhancedWorkflowRouter()
    validator = SessionValidator()
    if session_storage:
        validator.set_session_storage(session_storage)
    session_logger = SessionFlowLogger()

    session_phase_tracker: dict[str, WorkflowPhase] = {}
    cleanup_counter = 0

    @streamlined_node("email_workflow_orchestrator", WorkflowPhase.INITIALIZATION)
    async def email_workflow_orchestrator(
        state: UniversalWorkflowState,
    ) -> UniversalWorkflowState:
        """Coordinate email generation workflow with multi-agent patterns."""

        nonlocal cleanup_counter

        # Use defensive state access utilities for LangGraph state conversion
        # Always define fallback functions first
        def safe_get_fallback(state, key, expected_type=None, default=None):
            """Defensive generic state access."""
            try:
                value = getattr(state, key)
            except (AttributeError, TypeError):
                if isinstance(state, dict):
                    value = state.get(key, default)
                else:
                    value = default

            if value is None:
                return default

            if expected_type and callable(expected_type):
                try:
                    return expected_type(value)
                except (ValueError, TypeError):
                    return default

            return value

        try:
            from universal_framework.utils.state_access import (
                safe_get,
                safe_get_context_data,
                safe_get_messages,
                safe_get_phase,
                safe_get_session_id,
                safe_get_user_id,
            )
        except ImportError as e:
            logger.error(f"Failed to import state_access utilities: {e}")

            # Use fallback implementations for defensive programming
            def safe_get_session_id(state):
                """Defensive session ID extraction for both Pydantic and dict states."""
                try:
                    return state.session_id
                except AttributeError:
                    return state.get("session_id", "unknown")

            def safe_get_user_id(state):
                """Defensive user ID extraction for both Pydantic and dict states."""
                try:
                    return state.user_id
                except AttributeError:
                    return state.get("user_id", "unknown")

            def safe_get_phase(state):
                """Defensive phase extraction with proper type conversion."""
                try:
                    phase = state.workflow_phase
                except AttributeError:
                    phase = state.get("workflow_phase")

                if phase is None:
                    return WorkflowPhase.INITIALIZATION

                if isinstance(phase, str):
                    return WorkflowPhase(phase)
                elif isinstance(phase, WorkflowPhase):
                    return phase
                else:
                    return WorkflowPhase.INITIALIZATION

            def safe_get_context_data(state):
                """Defensive context data extraction."""
                try:
                    return state.context_data or {}
                except AttributeError:
                    return state.get("context_data", {})

            def safe_get_messages(state):
                """Defensive messages extraction."""
                try:
                    return state.messages or []
                except AttributeError:
                    return state.get("messages", [])

            # Use fallback for safe_get
            safe_get = safe_get_fallback

        session_id = safe_get_session_id(state)
        user_id = safe_get_user_id(state)

        if not await validator.validate_session_ownership(session_id, user_id):
            raise SessionSecurityError("Session ownership validation failed")

        prev_phase = session_phase_tracker.get(session_id)
        enhanced_state = state

        # Use defensive state access utilities for LangGraph state conversion
        current_workflow_phase = safe_get_phase(state)

        if prev_phase is None:
            session_phase_tracker[session_id] = current_workflow_phase
        elif prev_phase != current_workflow_phase:
            session_logger.log_workflow_phase_transition(
                session_id,
                user_id,
                from_phase=prev_phase.value,
                to_phase=current_workflow_phase.value,
            )
            enhanced_state = state.copy(update={"previous_phase": prev_phase})
            session_phase_tracker[session_id] = current_workflow_phase

        cleanup_counter += 1
        if cleanup_counter >= 1000 and len(session_phase_tracker) > 10000:
            for sid in list(session_phase_tracker)[: len(session_phase_tracker) - 5000]:
                session_phase_tracker.pop(sid, None)
            cleanup_counter = 0

        # Use defensive state access utilities for LangGraph state conversion
        current_phase = safe_get_phase(enhanced_state)

        messages = safe_get_messages(enhanced_state)
        orchestrator_messages = extract_agent_messages(
            messages, "email_workflow_orchestrator"
        )
        last_user_message = None

        for msg in reversed(messages):
            if msg.__class__.__name__ == "HumanMessage":
                last_user_message = msg
                break

        next_agent, routing_message, target_phase = _determine_next_agent_enhanced(
            current_phase,
            enhanced_state,
            orchestrator_messages,
            last_user_message,
            router,
        )

        # Handle phase transitions for ADVANCE_PHASE routing decisions
        final_state = enhanced_state
        if target_phase and target_phase != current_phase:
            final_state = enhanced_state.transition_to_phase(target_phase)
            # Update session tracking for the new phase using defensive session_id access
            session_phase_tracker[session_id] = target_phase
            session_logger.log_workflow_phase_transition(
                session_id,
                user_id,
                from_phase=current_phase.value,
                to_phase=target_phase.value,
            )

        # Use defensive state access utilities for LangGraph state conversion
        final_state_context = safe_get_context_data(final_state)
        final_state_phase_value = safe_get_phase(final_state).value
        final_state_messages = safe_get_messages(final_state)
        final_state_previous_phase = safe_get(
            final_state, "previous_phase", WorkflowPhase
        )

        if next_agent and next_agent != "END":
            # Use defensive state access utilities
            current_workflow_phase = safe_get_phase(final_state)

            agent_message = create_agent_message(
                from_agent="email_workflow_orchestrator",
                to_agent=next_agent,
                content=routing_message["content"],
                phase=current_workflow_phase,  # Use the safely retrieved phase
                data=routing_message.get(
                    "data", {}
                ),  # Defensive programming for data access
            )
            new_messages = final_state_messages + [agent_message]
        else:
            new_messages = final_state_messages

        updates = {
            "current_node": next_agent,
            "messages": new_messages,
            "context_data": {
                **final_state_context,
                "workflow_orchestration": {
                    "next_agent": next_agent,
                    "routing_reason": routing_message["reason"],
                    "timestamp": datetime.now().isoformat(),
                    "phase": final_state_phase_value,
                },
            },
        }

        if final_state_previous_phase is not None:
            updates["previous_phase"] = final_state_previous_phase

        return final_state.copy(update=updates)

    return email_workflow_orchestrator


def _determine_next_agent_enhanced(
    current_phase: WorkflowPhase,
    state: UniversalWorkflowState,
    orchestrator_messages: list[AgentMessage],
    last_user_message: Any | None,
    router: EnhancedWorkflowRouter,
) -> tuple[str, dict[str, Any], WorkflowPhase | None]:
    """Enhanced routing decision with error recovery and phase transition info."""

    # Agent to phase mapping
    agent_phase_map = {
        "batch_requirements_collector": WorkflowPhase.BATCH_DISCOVERY,
        "strategy_generator": WorkflowPhase.STRATEGY_ANALYSIS,
        "strategy_confirmation_handler": WorkflowPhase.STRATEGY_CONFIRMATION,
        "enhanced_email_generator": WorkflowPhase.GENERATION,
    }

    try:
        if last_user_message:
            command = _detect_global_command(last_user_message.content)
            if command:
                next_agent, response_message = _handle_global_command(command, state)
                return next_agent, response_message, None

        routing_result = router.route_from_node("email_workflow_orchestrator", state)

        response_message = {
            "content": f"Routing to {routing_result.next_node}",
            "target_phase": current_phase,
            "data": {},
            "reason": routing_result.routing_reason,
            "decision_type": routing_result.decision_type.value,
            "phase": current_phase.value,
            "timestamp": datetime.now().isoformat(),
            "performance_data": {
                "routing_time_ms": 0,
                "cache_hit": (
                    routing_result.metadata.get("cache_hit", False)
                    if routing_result.metadata
                    else False
                ),
            },
        }

        if routing_result.decision_type == RoutingDecision.ERROR_RECOVERY:
            response_message["recovery_path"] = routing_result.recovery_path
            response_message["escalation_needed"] = (
                routing_result.next_node == "escalation_handler"
            )

        # Determine target phase for phase transitions
        target_phase = None
        if routing_result.decision_type == RoutingDecision.ADVANCE_PHASE:
            target_phase = agent_phase_map.get(routing_result.next_node)
            if target_phase:
                response_message["target_phase"] = target_phase

        return routing_result.next_node, response_message, target_phase

    except Exception as e:  # noqa: BLE001
        error_message = {
            "content": "Routing system failure - escalating to failure analysis",
            "error": str(e),
            "phase": current_phase.value,
            "timestamp": datetime.now().isoformat(),
            "escalation_triggered": True,
        }

        e.add_note(f"Failed during enhanced routing from phase {current_phase}")

        return "failure_analyst", error_message, None


def _detect_global_command(message_content: str) -> str | None:
    """Detect global commands with pattern matching."""
    content_lower = message_content.lower().strip()
    match content_lower:
        case cmd if "restart" in cmd or "start over" in cmd:
            return "restart"
        case cmd if "debug" in cmd and ("enable" in cmd or "on" in cmd):
            return "debug_enable"
        case cmd if "debug" in cmd and ("disable" in cmd or "off" in cmd):
            return "debug_disable"
        case cmd if "go back" in cmd or "undo" in cmd or "previous" in cmd:
            return "go_back"
        case cmd if "help" in cmd or "?" in cmd:
            return "help"
        case cmd if "status" in cmd or "progress" in cmd:
            return "status"
        case _:
            return None


def _handle_global_command(
    command: str, state: UniversalWorkflowState
) -> tuple[str, dict[str, Any]]:
    """Handle global commands with simple routing."""

    # Defensive programming: safely get workflow_phase
    try:
        help_context = state.workflow_phase
    except AttributeError:
        # If state is dict, use dict access
        help_context = WorkflowPhase(
            state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
        )

    match command:
        case "restart":
            return "session_manager", {
                "content": "Restarting workflow...",
                "global_command": "restart",
                "preserve_context": False,
            }
        case "debug_enable":
            return "debug_controller", {
                "content": "Enabling debug mode...",
                "debug_action": "enable",
            }
        case "debug_disable":
            return "debug_controller", {
                "content": "Disabling debug mode...",
                "debug_action": "disable",
            }
        case "go_back":
            return "checkpoint_navigator", {
                "content": "Navigating to previous checkpoint...",
                "navigation_direction": "backward",
            }
        case "help":
            return "help_system", {
                "content": "Providing contextual assistance...",
                "help_context": help_context,  # Use the safely retrieved phase
            }
        case "status":
            return "progress_tracker", {
                "content": "Generating workflow status...",
                "status_request": True,
            }
        case _:
            return "conversation_orchestrator", {
                "content": f"Unknown global command: {command}",
                "error": "unrecognized_command",
            }
