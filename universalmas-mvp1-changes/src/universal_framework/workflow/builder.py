"""LangGraph StateGraph assembly with enterprise patterns and real agent integration."""

import os
from collections.abc import Callable
from datetime import datetime
from types import MethodType
from typing import Any

from langchain_core.runnables import RunnableConfig

try:  # langgraph>=0.5 uses memory saver
    from langgraph.checkpoint.sqlite import SqliteSaver

    SQLITE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):  # pragma: no cover - fallback
    from langgraph.checkpoint.memory import MemorySaver as SqliteSaver

    SQLITE_AVAILABLE = False
from universal_framework.compliance import (
    EnterpriseAuditManager,
    FailClosedStateValidator,
    PrivacySafeLogger,
)
from universal_framework.config.feature_flags import feature_flags
from universal_framework.contracts.nodes import register_validator
from universal_framework.contracts.redis.interfaces import (
    RedisSessionManagerInterface as RedisSessionManager,
)
from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.observability import UniversalFrameworkLogger
from universal_framework.workflow.orchestrator import (
    create_email_workflow_orchestrator,
)
from universal_framework.workflow.production_graph import (
    END,
    CompiledEnterpriseGraph,
    EnterpriseGraphConfig,
    EnterpriseStateGraph,
)
from universal_framework.workflow.routing import EnhancedWorkflowRouter

try:  # Optional concrete session manager
    from universal_framework.redis.session_manager import (
        RedisSessionManager as ConcreteRedisManager,
    )
except (
    ImportError,
    ModuleNotFoundError,
):  # pragma: no cover - fallback when implementation missing
    ConcreteRedisManager = None  # type: ignore

# Import simulation agents (always available)
from universal_framework.llm.providers import LLMConfig, LLMProvider, OpenAIProvider
from universal_framework.redis.session_storage import SessionStorage
from universal_framework.workflow.message_management import (
    MessageHistoryMode,
    create_message_aware_workflow_orchestrator,
)
from universal_framework.workflow.nodes import (
    batch_requirements_collector,
    enhanced_email_generator,
    strategy_confirmation_handler,
    strategy_generator,
)

# Legacy IntentClassificationNode removed - using unified IntentClassifierAgent approach

# Initialize logger
logger = UniversalFrameworkLogger("workflow_builder")

# Import configuration system
try:
    from universal_framework.config.factory import setup_observability

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# Import real agents (conditional)
# Legacy agent imports removed - using modern node-based agents only
REAL_AGENTS_AVAILABLE = False  # Force use of modern node-based agents
try:
    # Dummy try block for consistency with existing code structure
    pass
except ImportError:
    REAL_AGENTS_AVAILABLE = False
    real_requirements_collector = None


class WorkflowBuilder:
    """Factory for workflow agents with optional LLM provider injection."""

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or self._create_default_provider()

    def _create_default_provider(self) -> LLMProvider:
        config = LLMConfig.from_env()
        return OpenAIProvider(config=config)

    # Modern node-based agent factory methods
    def create_requirements_agent(self):
        """Create modern requirements collection agent."""
        from universal_framework.nodes.agents import RequirementsCollectionAgent

        return RequirementsCollectionAgent()

    def create_strategy_generator_agent(self):
        """Create modern strategy generation agent."""
        from universal_framework.nodes.agents import StrategyGenerationAgent

        return StrategyGenerationAgent()

    def create_email_generator_agent(self):
        """Create modern email generation agent."""
        from universal_framework.nodes.agents import EmailGenerationAgent

        return EmailGenerationAgent()

    def create_confirmation_agent(self):
        """Create modern intent analysis agent for confirmation."""
        from universal_framework.nodes.agents import IntentAnalysisAgent

        return IntentAnalysisAgent()


def create_streamlined_workflow(
    checkpointer: SqliteSaver | None = None,
    enable_parallel: bool = False,
    performance_config: dict[str, Any] | None = None,
    enable_debug: bool = False,
    redis_session_manager: RedisSessionManager | None = None,
    message_history_mode: MessageHistoryMode = MessageHistoryMode.FULL_HISTORY,
    use_real_agents: bool = True,  # NEW: Toggle for real vs simulation agents
    llm_config_path: str | None = None,  # NEW: Custom config path
    llm_provider: LLMProvider | None = None,
    enable_compliance: bool = True,
    compliance_config: dict[str, Any] | None = None,
    session_storage: SessionStorage | None = None,
    **message_history_kwargs: Any,
) -> CompiledEnterpriseGraph:
    """
    Create enterprise-grade email workflow with LangGraph patterns, message history management, and real agent integration.

    Args:
        checkpointer: State persistence (default: in-memory SQLite)
        enable_parallel: Enable parallel agent execution patterns
        performance_config: Performance tuning parameters
        enable_debug: Enable debug mode with interrupts
        redis_session_manager: Optional Redis manager for session optimization
        message_history_mode: Message filtering strategy (default: FULL_HISTORY)
        use_real_agents: Use real LangChain agents vs simulations (default: True)
        llm_config_path: Optional path to TOML config file
        **message_history_kwargs: Additional configuration for message filters
            - window_size (int): For SLIDING_WINDOW mode (default: 10)
            - summary_threshold (int): For SUMMARIZED mode (default: 20)
            - keep_recent (int): For SUMMARIZED mode (default: 5)
            - included_roles (list[str]): For ROLE_FILTERED mode

    Returns:
        Compiled LangGraph StateGraph ready for execution with message management and real agents

    Examples:
        # Standard workflow with real agents
        workflow = create_streamlined_workflow()

        # Testing workflow with simulations only
        workflow = create_streamlined_workflow(use_real_agents=False)

        # Memory-optimized workflow with sliding window
        workflow = create_streamlined_workflow(
            message_history_mode=MessageHistoryMode.SLIDING_WINDOW,
            window_size=20,
            use_real_agents=True
        )

        # Custom configuration workflow
        workflow = create_streamlined_workflow(
            llm_config_path="config/custom.toml",
            use_real_agents=True,
            enable_debug=True
        )
    """

    # Setup observability if available and safe mode allows
    if CONFIG_AVAILABLE and feature_flags.is_enabled("LANGSMITH_TRACING"):
        setup_observability()

    # Initialize workflow builder with optional provider
    workflow_builder = WorkflowBuilder(llm_provider=llm_provider)

    # Enterprise compliance components
    validator: FailClosedStateValidator | None = None
    if enable_compliance:
        from universal_framework.config.compliance_loader import load_compliance_config

        _ = load_compliance_config()  # Placeholder for future use
        privacy_logger = PrivacySafeLogger()

        if feature_flags.is_enabled("ENTERPRISE_FEATURES"):
            from universal_framework.observability.enterprise_langsmith import (
                EnterpriseLangSmithConfig,
            )

            langsmith_config = EnterpriseLangSmithConfig()
            audit_manager = EnterpriseAuditManager(privacy_logger, langsmith_config)
            validator = FailClosedStateValidator(audit_manager)
        else:
            # Use safe mode - no enterprise audit manager in safe mode
            validator = None

    # Initialize performance configuration
    perf_config = performance_config or {
        "max_execution_time": 30.0,  # seconds
        "agent_timeout": 5.0,  # seconds per agent
        "checkpoint_interval": 10,  # save every N steps
        "enable_metrics": True,
        "message_management_enabled": message_history_mode
        != MessageHistoryMode.FULL_HISTORY,
        "message_filter_mode": message_history_mode.value,
        "use_real_agents": use_real_agents,
    }

    # Create EnterpriseStateGraph with UniversalWorkflowState
    graph_config = EnterpriseGraphConfig(
        enable_compliance=enable_compliance,
    )
    workflow = EnterpriseStateGraph(UniversalWorkflowState, graph_config)

    # Determine which agents to use
    agents = _select_agents(use_real_agents, workflow_builder, llm_config_path)

    # Create orchestrator with conditional message history management
    available_agents = list(agents.keys())

    if message_history_mode != MessageHistoryMode.FULL_HISTORY:
        email_orchestrator = create_message_aware_workflow_orchestrator(
            available_agents,
            redis_session_manager=redis_session_manager,
            message_history_mode=message_history_mode,
            session_storage=session_storage,
            **message_history_kwargs,
        )
    else:
        email_orchestrator = create_email_workflow_orchestrator(
            available_agents, session_storage=session_storage
        )

    if validator:
        email_orchestrator._validator = validator

    workflow.add_node("email_workflow_orchestrator", email_orchestrator)

    # Add enhanced intent classifier agent as entry point (unified approach)
    from universal_framework.nodes.agents import IntentClassifierAgent

    intent_classifier = IntentClassifierAgent(enable_conversation_aware=True)

    async def intent_classifier_node(
        state: UniversalWorkflowState,
    ) -> UniversalWorkflowState:
        """Enhanced intent classification node with conversation awareness."""
        # Local logger for this function
        local_logger = UniversalFrameworkLogger("intent_classifier_node")

        try:
            # Extract user input safely
            messages = (
                state.messages
                if hasattr(state, "messages")
                else state.get("messages", [])
            )
            if not messages:
                # Create fallback state for missing messages
                return state.copy(
                    update={
                        "intent_classification_result": {
                            "intent": "general_conversation",
                            "confidence": 0.3,
                            "message_type": "route_to_workflow",
                            "routing_destination": "email_workflow_orchestrator",
                            "metadata": {
                                "error": "no_messages",
                                "classification_method": "fallback",
                            },
                        }
                    }
                )

            # Get last user message - FIXED: Handle None name attribute
            last_user_message = None
            for msg in reversed(messages):
                if hasattr(msg, "content"):
                    msg_name = getattr(msg, "name", "") or ""  # Handle None case
                    if not msg_name.startswith("assistant"):
                        last_user_message = msg.content
                        break

            if not last_user_message:
                # Create fallback for no user input
                return state.copy(
                    update={
                        "intent_classification_result": {
                            "intent": "general_conversation",
                            "confidence": 0.3,
                            "message_type": "route_to_workflow",
                            "routing_destination": "email_workflow_orchestrator",
                            "metadata": {
                                "error": "no_user_message",
                                "classification_method": "fallback",
                            },
                        }
                    }
                )

            # Execute intent classification
            classification_result = await intent_classifier.execute(
                user_input=last_user_message, state=state, timeout=30.0
            )

            # Map result to expected format
            intent_result = {
                "intent": classification_result.get("intent", "general_conversation"),
                "confidence": classification_result.get("confidence", 0.5),
                "message_type": (
                    "route_to_workflow"
                    if classification_result.get("intent")
                    not in ["help_request", "greeting"]
                    else "help_response"
                ),
                "routing_destination": "email_workflow_orchestrator",
                "metadata": {
                    "classification_method": classification_result.get(
                        "classification_method", "llm"
                    ),
                    "conversation_aware": classification_result.get(
                        "conversation_aware", True
                    ),
                    "user_input_length": len(last_user_message),
                    "original_result": classification_result,
                },
            }

            return state.copy(
                update={
                    "intent_classification_result": intent_result,
                    "context_data": {
                        **(
                            state.context_data
                            if hasattr(state, "context_data")
                            else state.get("context_data", {})
                        ),
                        "classified_intent": intent_result["intent"],
                        "message_type": intent_result["message_type"],
                    },
                }
            )

        except (AttributeError, KeyError, TypeError, TimeoutError) as e:
            local_logger.error(f"Intent classification failed: {e}")
            # Graceful fallback
            return state.copy(
                update={
                    "intent_classification_result": {
                        "intent": "general_conversation",
                        "confidence": 0.3,
                        "message_type": "route_to_workflow",
                        "routing_destination": "email_workflow_orchestrator",
                        "metadata": {
                            "error": str(e),
                            "classification_method": "error_fallback",
                        },
                    }
                }
            )

    workflow.add_node("intent_classifier", intent_classifier_node)

    # Add selected agents (real or simulation)
    for agent_name, agent_func in agents.items():
        if validator:
            if isinstance(agent_func, MethodType):
                agent_func.__func__._validator = validator
            else:
                agent_func._validator = validator
        workflow.add_node(agent_name, agent_func)

    # Add optional parallel processing nodes
    if enable_parallel:
        workflow.add_node("quality_validator", _create_quality_validator())
        workflow.add_node("delivery_coordinator", _create_delivery_coordinator())

    # Set intent classifier as entry point instead of orchestrator (SalesGPT pattern)
    workflow.set_entry_point("intent_classifier")

    # Add conditional routing from intent classifier (similar to SalesGPT stage routing)
    def intent_router(state: UniversalWorkflowState) -> str:
        """Route based on intent classification results (SalesGPT-inspired pattern)."""
        # Use defensive state access for LangGraph state conversion
        try:
            from universal_framework.utils.state_access import safe_get

            intent_result = safe_get(state, "intent_classification_result", dict, {})
            message_type = intent_result.get("message_type", "route_to_workflow")

            # Route based on message type (following SalesGPT conversation stage pattern)
            match message_type:
                case "help_response" | "phase_specific_help":
                    return END  # Help responses are handled by intent classifier
                case "route_to_workflow" | "email_request":
                    return "email_workflow_orchestrator"  # Continue to workflow
                case _:
                    return "email_workflow_orchestrator"  # Default to workflow
        except (ImportError, AttributeError, KeyError, TypeError):
            # Fallback to orchestrator on state access or routing errors
            return "email_workflow_orchestrator"

    workflow.add_conditional_edges(
        "intent_classifier",
        intent_router,
        {
            "email_workflow_orchestrator": "email_workflow_orchestrator",
            END: END,
        },
    )

    # Add orchestrator-driven routing
    workflow.add_conditional_edges(
        "email_workflow_orchestrator",
        _create_workflow_phase_router(),
        {
            "batch_requirements_collector": "batch_requirements_collector",
            "strategy_generator": "strategy_generator",
            "strategy_confirmation_handler": "strategy_confirmation_handler",
            "enhanced_email_generator": "enhanced_email_generator",
            END: END,
        },
    )

    # All agents report back to orchestrator (centralized coordination)
    for agent_name in available_agents:
        workflow.add_edge(agent_name, "email_workflow_orchestrator")

    # Add parallel processing edges (if enabled)
    if enable_parallel:
        workflow.add_edge(
            "enhanced_email_generator", ["quality_validator", "delivery_coordinator"]
        )
        workflow.add_edge(["quality_validator", "delivery_coordinator"], END)

    # Configure checkpointing
    if checkpointer is None:
        if SQLITE_AVAILABLE:
            checkpointer = SqliteSaver.from_conn_string(":memory:")
        else:
            checkpointer = SqliteSaver()  # MemorySaver doesn't use from_conn_string

    # Compile with enterprise configuration and recursion limits
    interrupt_nodes = []
    if enable_debug:
        interrupt_nodes = ["strategy_confirmation_handler"]

    # Enhanced compilation configuration following LangGraph best practices
    compile_config = {"checkpointer": checkpointer, "interrupt_before": interrupt_nodes}

    # Try to compile with recursion_limit (newer LangGraph versions)
    try:
        compile_config["recursion_limit"] = (
            200  # Further increased limit for production robustness
        )
        compiled_workflow = workflow.compile(**compile_config)
    except TypeError as e:
        # Fallback for older LangGraph versions that don't support recursion_limit
        if "recursion_limit" in str(e):
            compile_config.pop("recursion_limit", None)
            compiled_workflow = workflow.compile(**compile_config)
        else:
            # Re-raise if it's a different TypeError
            raise
    except (RuntimeError, ImportError, AttributeError, ValueError) as e:
        # Enhanced error reporting for compilation issues
        raise RuntimeError(f"LangGraph workflow compilation failed: {e}") from e

    if validator:
        workflow_id = f"wf_{datetime.now().timestamp()}"
        register_validator(workflow_id, validator)
        compiled_workflow._validator = validator
        compiled_workflow._workflow_id = workflow_id

    # Add performance monitoring wrapper
    if perf_config.get("enable_metrics"):
        compiled_workflow = _add_performance_monitoring(compiled_workflow, perf_config)

    # Placeholder for enhanced logging details removed after refactor
    return compiled_workflow


def create_enhanced_workflow(
    use_case_config: dict[str, Any] | None = None,
    checkpointer: SqliteSaver | None = None,
    enable_parallel: bool = False,
    performance_config: dict[str, Any] | None = None,
    enable_debug: bool = False,
    redis_session_manager: Any | None = None,
    llm_provider: LLMProvider | None = None,
) -> CompiledEnterpriseGraph:
    """Create enhanced workflow with comprehensive routing."""

    perf_config = performance_config or {
        "max_execution_time": 30.0,
        "agent_timeout": 5.0,
        "checkpoint_interval": 5,
        "enable_metrics": True,
        "routing_cache_size": 1000,
        "error_recovery_enabled": True,
    }

    router = EnhancedWorkflowRouter(
        use_case_config=use_case_config,
        performance_mode=perf_config.get("routing_cache_size", 0) > 0,
    )

    workflow_builder = WorkflowBuilder(llm_provider=llm_provider)

    graph_config = EnterpriseGraphConfig(enable_compliance=True)
    workflow = EnterpriseStateGraph(UniversalWorkflowState, graph_config)

    agents = _get_universal_agent_list(use_case_config)
    for agent_name in agents:
        workflow.add_node(
            agent_name,
            _create_enhanced_agent_node(agent_name, workflow_builder=workflow_builder),
        )

    _add_enhanced_conditional_edges(workflow, router, agents)

    entry_point = agents[0] if agents else "email_workflow_orchestrator"
    workflow.set_entry_point(entry_point)

    if checkpointer is None:
        if SQLITE_AVAILABLE:
            enhanced_checkpointer = SqliteSaver.from_conn_string(":memory:")
        else:
            enhanced_checkpointer = (
                SqliteSaver()
            )  # MemorySaver doesn't use from_conn_string
    else:
        enhanced_checkpointer = checkpointer
    compiled_workflow = workflow.compile(
        checkpointer=enhanced_checkpointer,
        interrupt_before=(
            ["escalation_handler", "human_intervention"] if enable_debug else None
        ),
        interrupt_after=["failure_analyst"] if enable_debug else None,
    )

    return compiled_workflow


def _select_agents(
    use_real_agents: bool,
    workflow_builder: WorkflowBuilder,
    llm_config_path: str | None = None,
) -> dict[str, Callable]:
    """Select between real and simulated agents with comprehensive real agent support."""

    if use_real_agents:
        try:
            from universal_framework.nodes.batch_requirements_collector import (
                BatchRequirementsCollectorNode,
            )
            from universal_framework.nodes.enhanced_email_generator import (
                EnhancedEmailGeneratorNode,
            )
            from universal_framework.nodes.strategy_confirmation_handler import (
                StrategyConfirmationHandler,
            )
            from universal_framework.nodes.strategy_generator_node import (
                StrategyGeneratorNode,
            )

            real_nodes = {
                "batch_requirements_collector": BatchRequirementsCollectorNode().execute,
                "strategy_generator": StrategyGeneratorNode().execute,
                "strategy_confirmation_handler": StrategyConfirmationHandler().execute,
                "enhanced_email_generator": EnhancedEmailGeneratorNode().execute,
            }

            return real_nodes

        except ImportError:
            # Real agents not available, fall back to mock agents
            pass
        except (AttributeError, ModuleNotFoundError, TypeError):
            # Agent initialization failed, fall back to mock agents
            pass

    return {
        "batch_requirements_collector": batch_requirements_collector,
        "strategy_generator": strategy_generator,
        "strategy_confirmation_handler": strategy_confirmation_handler,
        "enhanced_email_generator": enhanced_email_generator,
    }


def _is_real_agent(agent_func: Callable) -> bool:
    """Determine if agent function is real or simulation."""

    # Check if function name suggests it's real
    if hasattr(agent_func, "__name__"):
        return agent_func.__name__.startswith("real_")

    # Check module path
    if hasattr(agent_func, "__module__"):
        return "agents." in agent_func.__module__

    return False


def _get_universal_agent_list(
    use_case_config: dict[str, Any] | None = None,
) -> list[str]:
    """Return list of universal agents for enhanced workflow."""
    return [
        "batch_requirements_collector",
        "strategy_generator",
        "strategy_confirmation_handler",
        "enhanced_email_generator",
    ]


def _create_enhanced_agent_node(
    agent_name: str,
    use_real_agents: bool = True,
    workflow_builder: WorkflowBuilder | None = None,
    llm_config_path: str | None = None,
) -> Callable[[UniversalWorkflowState], UniversalWorkflowState]:
    """Create enhanced agent node that executes real agents with error recovery."""

    async def enhanced_agent_node(
        state: UniversalWorkflowState,
    ) -> UniversalWorkflowState:
        import asyncio
        import time

        from universal_framework.workflow.error_recovery import AgentCircuitBreaker

        try:
            from universal_framework.observability.simple_metrics import (
                measure_agent_execution,
            )
        except (
            ImportError,
            ModuleNotFoundError,
        ):  # pragma: no cover - metrics optional
            from contextlib import (
                nullcontext as measure_agent_execution,  # type: ignore
            )

        start_time = time.time()
        circuit_breaker = AgentCircuitBreaker()

        try:
            agents = _select_agents(use_real_agents, workflow_builder, llm_config_path)
            if agent_name not in agents:
                # Defensive programming for LangGraph state conversion
                recovery_attempts = (
                    state.recovery_attempts
                    if hasattr(state, "recovery_attempts")
                    else state.get("recovery_attempts", {})
                )
                error_recovery_state = (
                    state.error_recovery_state
                    if hasattr(state, "error_recovery_state")
                    else state.get("error_recovery_state", {})
                )
                context_data = (
                    state.context_data
                    if hasattr(state, "context_data")
                    else state.get("context_data", {})
                )

                error_ctx = {
                    "error_type": "agent_not_found",
                    "retry_count": recovery_attempts.get(agent_name, 0),
                    "original_error": f"Agent {agent_name} unavailable",
                }
                exec_ms = (time.time() - start_time) * 1000
                return state.copy(
                    update={
                        "error_recovery_state": {
                            **error_recovery_state,
                            agent_name: error_ctx,
                        },
                        "recovery_attempts": {
                            **recovery_attempts,
                            agent_name: error_ctx["retry_count"] + 1,
                        },
                        "context_data": {
                            **context_data,
                            "last_error": error_ctx,
                            "agent_execution_failed": True,
                        },
                    }
                )

            agent_func = agents[agent_name]
            is_real_agent = _is_real_agent(agent_func)

            with measure_agent_execution(agent_name, is_real_agent):
                if asyncio.iscoroutinefunction(agent_func):
                    result_state = await circuit_breaker.execute_with_fallback(
                        agent_func,
                        lambda s=state: s,
                        state,
                    )[0]
                else:
                    result_state, _ = await circuit_breaker.execute_with_fallback(
                        asyncio.to_thread, agent_func, state
                    )

            if not isinstance(result_state, UniversalWorkflowState):
                raise ValueError(
                    f"Agent {agent_name} returned invalid state type: {type(result_state)}"
                )

            exec_ms = (time.time() - start_time) * 1000
            meta = {
                "agent_name": agent_name,
                "execution_time_ms": exec_ms,
                "is_real_agent": is_real_agent,
                "timestamp": datetime.now().isoformat(),
                "success": True,
            }

            return result_state.copy(
                update={
                    "context_data": {
                        **(
                            result_state.context_data
                            if hasattr(result_state, "context_data")
                            else result_state.get("context_data", {})
                        ),
                        "last_agent_execution": meta,
                        "agent_execution_failed": False,
                    },
                    "audit_trail": [
                        *(
                            result_state.audit_trail
                            if hasattr(result_state, "audit_trail")
                            else result_state.get("audit_trail", [])
                        ),
                        meta,
                    ],
                }
            )

        except (AttributeError, KeyError, TypeError, RuntimeError, TimeoutError) as exc:
            exec_ms = (time.time() - start_time) * 1000
            # Defensive programming for LangGraph state conversion
            recovery_attempts = (
                state.recovery_attempts
                if hasattr(state, "recovery_attempts")
                else state.get("recovery_attempts", {})
            )
            error_recovery_state = (
                state.error_recovery_state
                if hasattr(state, "error_recovery_state")
                else state.get("error_recovery_state", {})
            )
            context_data = (
                state.context_data
                if hasattr(state, "context_data")
                else state.get("context_data", {})
            )
            audit_trail = (
                state.audit_trail
                if hasattr(state, "audit_trail")
                else state.get("audit_trail", [])
            )

            error_ctx = {
                "error_type": "execution_failure",
                "retry_count": recovery_attempts.get(agent_name, 0),
                "original_error": str(exc),
                "execution_time_ms": exec_ms,
                "agent_name": agent_name,
            }
            exc.add_note(f"Agent execution failure in {agent_name}")
            return state.copy(
                update={
                    "error_recovery_state": {
                        **error_recovery_state,
                        agent_name: error_ctx,
                    },
                    "recovery_attempts": {
                        **recovery_attempts,
                        agent_name: error_ctx["retry_count"] + 1,
                    },
                    "context_data": {
                        **context_data,
                        "last_error": error_ctx,
                        "agent_execution_failed": True,
                        "failed_agent": agent_name,
                    },
                    "audit_trail": [
                        *audit_trail,
                        {
                            "agent_name": agent_name,
                            "execution_time_ms": exec_ms,
                            "success": False,
                            "error": str(exc),
                            "timestamp": datetime.now().isoformat(),
                        },
                    ],
                }
            )

    return enhanced_agent_node


def _add_enhanced_conditional_edges(
    workflow: EnterpriseStateGraph,
    router: EnhancedWorkflowRouter,
    universal_agents: list[str],
) -> None:
    """Add conditional edges for enhanced workflow."""

    for agent_name in universal_agents:
        routing_function = _create_agent_routing_function(agent_name, router)
        mapping = {node: node for node in router.get_possible_next_nodes(agent_name)}
        mapping[END] = END
        workflow.add_conditional_edges(agent_name, routing_function, mapping)


def _create_agent_routing_function(
    agent_name: str, router: EnhancedWorkflowRouter
) -> Callable[[UniversalWorkflowState], str]:
    """Return routing callable for agent."""

    def route(state: UniversalWorkflowState) -> str:
        result = router.route_from_node(agent_name, state)
        return result.next_node

    return route


def _create_workflow_phase_router():
    """Route based on orchestrator's routing decisions in context_data."""

    def route_from_orchestrator(state: UniversalWorkflowState) -> str:
        """
        LangGraph conditional edge routing function following best practices.
        Must handle all possible states and return valid node names or END.
        """
        try:
            # Ensure state is proper UniversalWorkflowState type - defensive programming for LangGraph state conversion
            context_data = (
                state.context_data
                if hasattr(state, "context_data")
                else state.get("context_data", {})
            )
            if not context_data:
                # Defensive programming: if state lost type, return END
                return END

            routing_info = context_data.get("workflow_orchestration", {})
            next_agent = routing_info.get("next_agent", END)

            # Explicit valid agent list matching graph nodes
            valid_agents = [
                "batch_requirements_collector",
                "strategy_generator",
                "strategy_confirmation_handler",
                "enhanced_email_generator",
            ]

            # Exhaustive routing with proper fallback
            if next_agent in valid_agents:
                return next_agent
            elif next_agent == "END" or next_agent == END:
                return END
            else:
                # Default fallback for any unexpected routing decisions
                return END

        except (AttributeError, KeyError, TypeError):
            # Circuit breaker: if routing fails, end workflow safely
            return END

    return route_from_orchestrator


def _create_quality_validator():
    """Create quality validation agent for parallel processing demo."""

    from universal_framework.contracts.nodes import streamlined_node

    @streamlined_node("quality_validator", WorkflowPhase.REVIEW)
    async def quality_validator(
        state: UniversalWorkflowState,
    ) -> UniversalWorkflowState:
        """Validate email quality in parallel."""

        # Defensive programming for LangGraph state conversion
        context_data = (
            state.context_data
            if hasattr(state, "context_data")
            else state.get("context_data", {})
        )
        generated_email = context_data.get("generated_email", {})

        # Simulate quality validation
        quality_score = 0.9 if generated_email else 0.0

        updates = {
            "context_data": {
                **context_data,
                "quality_validation": {
                    "score": quality_score,
                    "passed": quality_score >= 0.8,
                    "timestamp": datetime.now().isoformat(),
                },
            }
        }

        return state.copy(update=updates)

    return quality_validator


def _create_delivery_coordinator():
    """Create delivery coordination agent for parallel processing demo."""

    from universal_framework.contracts.nodes import streamlined_node

    @streamlined_node("delivery_coordinator", WorkflowPhase.DELIVERY)
    async def delivery_coordinator(
        state: UniversalWorkflowState,
    ) -> UniversalWorkflowState:
        """Coordinate email delivery in parallel."""

        # Defensive programming for LangGraph state conversion
        context_data = (
            state.context_data
            if hasattr(state, "context_data")
            else state.get("context_data", {})
        )
        generated_email = context_data.get("generated_email", {})

        # Simulate delivery preparation
        delivery_ready = bool(generated_email)

        updates = {
            "workflow_phase": WorkflowPhase.DELIVERY,
            "context_data": {
                **context_data,
                "delivery_status": {
                    "ready": delivery_ready,
                    "format": "html",
                    "timestamp": datetime.now().isoformat(),
                },
            },
        }

        return state.copy(update=updates)

    return delivery_coordinator


def _add_performance_monitoring(
    workflow: CompiledEnterpriseGraph, config: dict[str, Any]
) -> CompiledEnterpriseGraph:
    """Add actual performance monitoring to workflow."""

    if not config.get("enable_metrics", False):
        return workflow

    try:
        from universal_framework.observability.simple_metrics import (
            get_metrics_summary,
            record_workflow_phase_transition,
        )

        get_metrics_summary()

        # Placeholder for future node-wrapping metrics integration
        record_workflow_phase_transition("init", "init")

        return workflow

    except (ImportError, ModuleNotFoundError, AttributeError):
        # Metrics module unavailable - graceful degradation
        return workflow


# Utility functions for workflow execution


async def execute_workflow_step(
    workflow: CompiledEnterpriseGraph,
    state: UniversalWorkflowState,
    config: RunnableConfig | None = None,
) -> UniversalWorkflowState:
    """Execute single workflow step for API integration."""

    if config is None:
        # Defensive programming for LangGraph state conversion
        session_id = (
            state.session_id
            if hasattr(state, "session_id")
            else state.get("session_id", "default")
        )
        config = RunnableConfig(configurable={"thread_id": session_id})

    try:
        result = await workflow.ainvoke(state, config=config)
        return result
    except (RuntimeError, TimeoutError, ValueError, KeyError) as e:
        # Return error state for workflow execution failures
        return state.copy(
            update={
                "error_info": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "node": "workflow_execution",
                    "timestamp": datetime.now().isoformat(),
                }
            }
        )


def validate_workflow_state(state: UniversalWorkflowState) -> dict[str, Any]:
    """Validate workflow state consistency."""

    validation_results = {"valid": True, "errors": [], "warnings": []}

    # Basic validation - defensive programming for LangGraph state conversion
    session_id = (
        state.session_id
        if hasattr(state, "session_id")
        else state.get("session_id", None)
    )
    if not session_id:
        validation_results["errors"].append("Missing session_id")
        validation_results["valid"] = False

    # Check user_id with defensive programming
    user_id = state.user_id if hasattr(state, "user_id") else state.get("user_id", None)
    if not user_id:
        validation_results["errors"].append("Missing user_id")
        validation_results["valid"] = False

    # Phase-specific validation - defensive programming for workflow_phase
    try:
        phase = (
            state.workflow_phase
            if hasattr(state, "workflow_phase")
            else state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
        )
        if isinstance(phase, str):
            phase = WorkflowPhase(phase)
    except (AttributeError, ValueError):
        # If state is dict or invalid phase, use default
        phase = WorkflowPhase(
            state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
            if isinstance(state, dict)
            else WorkflowPhase.INITIALIZATION
        )

    # Context data access with defensive programming
    context_data = (
        state.context_data
        if hasattr(state, "context_data")
        else state.get("context_data", {})
    )

    if phase == WorkflowPhase.STRATEGY_ANALYSIS and not context_data.get(
        "collected_requirements"
    ):
        validation_results["warnings"].append(
            "No requirements collected for strategy analysis"
        )

    elif phase == WorkflowPhase.STRATEGY_CONFIRMATION and not context_data.get(
        "generated_strategy"
    ):
        validation_results["errors"].append("No strategy generated for confirmation")
        validation_results["valid"] = False

    elif phase == WorkflowPhase.GENERATION and not context_data.get(
        "approved_strategy"
    ):
        validation_results["warnings"].append("No approved strategy for generation")

    return validation_results


# Factory functions for common configurations


def create_memory_optimized_workflow(
    summary_threshold: int = 50,
    keep_recent: int = 10,
    redis_url: str | None = None,
    use_real_agents: bool = True,
) -> CompiledEnterpriseGraph:
    """Create workflow optimized for long conversations with intelligent summarization."""

    redis_manager = (
        ConcreteRedisManager(redis_url) if redis_url and ConcreteRedisManager else None
    )

    return create_streamlined_workflow(
        redis_session_manager=redis_manager,
        message_history_mode=MessageHistoryMode.SUMMARIZED,
        summary_threshold=summary_threshold,
        keep_recent=keep_recent,
        use_real_agents=use_real_agents,
    )


def create_development_workflow(
    debug_mode: bool = True, use_real_agents: bool = True
) -> CompiledEnterpriseGraph:
    """Create development workflow with full history, debug capabilities, and real agents if available."""

    return create_streamlined_workflow(
        enable_debug=debug_mode,
        message_history_mode=MessageHistoryMode.FULL_HISTORY,
        use_real_agents=use_real_agents,
    )


def create_testing_workflow() -> CompiledEnterpriseGraph:
    """Create testing workflow with simulations for reliable tests."""

    return create_streamlined_workflow(
        enable_debug=False,
        use_real_agents=False,  # Always use simulations for tests
        message_history_mode=MessageHistoryMode.FULL_HISTORY,
        performance_config={"enable_metrics": False},
    )


def create_production_workflow() -> CompiledEnterpriseGraph:
    """Create production workflow with environment-driven configuration."""

    redis_url = os.environ.get("REDIS_URL")
    redis_manager = (
        ConcreteRedisManager(redis_url) if redis_url and ConcreteRedisManager else None
    )

    mode_str = os.environ.get("MESSAGE_HISTORY_MODE", "summarized").upper()
    try:
        message_mode = MessageHistoryMode(mode_str.lower())
    except ValueError:
        message_mode = MessageHistoryMode.SUMMARIZED

    message_kwargs: dict[str, Any] = {}
    if message_mode == MessageHistoryMode.SUMMARIZED:
        message_kwargs.update(
            {
                "summary_threshold": int(
                    os.environ.get("MESSAGE_SUMMARY_THRESHOLD", "100")
                ),
                "keep_recent": int(os.environ.get("MESSAGE_KEEP_RECENT", "15")),
            }
        )
    elif message_mode == MessageHistoryMode.SLIDING_WINDOW:
        message_kwargs.update(
            {"window_size": int(os.environ.get("MESSAGE_WINDOW_SIZE", "25"))}
        )

    # Real agents in production (with fallback to simulations)
    use_real_agents = os.environ.get("USE_REAL_AGENTS", "true").lower() == "true"

    return create_streamlined_workflow(
        redis_session_manager=redis_manager,
        message_history_mode=message_mode,
        enable_parallel=os.environ.get("ENABLE_PARALLEL_PROCESSING", "false") == "true",
        enable_debug=False,
        use_real_agents=use_real_agents,
        **message_kwargs,
    )


# Legacy compatibility function
def create_redis_optimized_workflow(redis_url: str) -> CompiledEnterpriseGraph:
    """Create workflow with Redis optimization enabled (legacy compatibility)."""

    redis_manager = ConcreteRedisManager(redis_url) if ConcreteRedisManager else None
    return create_streamlined_workflow(
        redis_session_manager=redis_manager, use_real_agents=True
    )
