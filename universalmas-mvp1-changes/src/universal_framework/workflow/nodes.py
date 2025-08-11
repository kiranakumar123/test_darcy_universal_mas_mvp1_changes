"""Email workflow nodes implementing multi-agent orchestration patterns."""

from datetime import datetime

from universal_framework.contracts.messages import create_agent_message
from universal_framework.contracts.nodes import streamlined_node
from universal_framework.contracts.state import (
    EmailRequirements,
    UniversalWorkflowState,
    WorkflowPhase,
)
from universal_framework.nodes.agents import StrategyGenerationAgent
from universal_framework.nodes.batch_requirements_collector import (
    BatchRequirementsCollectorNode,
)
from universal_framework.nodes.enhanced_email_generator import (
    create_enhanced_email_generator_node as enhanced_email_generator,  # noqa: F401 - re-exported for workflow usage
)
from universal_framework.nodes.strategy_confirmation_handler import (
    StrategyConfirmationHandler,
)


@streamlined_node("batch_requirements_collector", WorkflowPhase.BATCH_DISCOVERY)
async def batch_requirements_collector(
    state: UniversalWorkflowState,
) -> UniversalWorkflowState:
    """Real batch requirements collector using enhanced node implementation."""
    collector = BatchRequirementsCollectorNode()
    result_state = await collector.execute(state)

    # Add component tracking for enterprise monitoring
    component_status = "completed" if result_state.email_requirements else "incomplete"

    return result_state.copy(
        update={
            "component_status": {
                **result_state.component_status,
                "batch_requirements_collector": component_status,
            }
        }
    )


@streamlined_node("strategy_generator", WorkflowPhase.STRATEGY_ANALYSIS)
async def strategy_generator(state: UniversalWorkflowState) -> UniversalWorkflowState:
    """Real strategy generator using StrategyGenerator with enhanced state management."""
    start_time = datetime.now()

    # Validate requirements before strategy generation
    requirements_data = (
        state.context_data
        if hasattr(state, "context_data")
        else state.get("context_data", {})
    ).get("collected_requirements")
    if not requirements_data and not state.email_requirements:
        error_audit = {
            "timestamp": datetime.now().isoformat(),
            "node": "strategy_generator",
            "action": "generation_failed",
            "error": "missing_requirements",
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }

        msg = create_agent_message(
            "strategy_generator",
            "email_workflow_orchestrator",
            "Strategy generation failed: missing requirements",
            WorkflowPhase.STRATEGY_ANALYSIS,
            data={"error": "missing_requirements"},
        )

        return state.copy(
            update={
                "messages": [
                    *(
                        state.messages
                        if hasattr(state, "messages")
                        else state.get("messages", [])
                    ),
                    msg,
                ],
                "workflow_phase": WorkflowPhase.BATCH_DISCOVERY,
                "component_status": {
                    **(
                        state.component_status
                        if hasattr(state, "component_status")
                        else state.get("component_status", {})
                    ),
                    "strategy_generator": "failed",
                },
                "audit_trail": [
                    *(
                        state.audit_trail
                        if hasattr(state, "audit_trail")
                        else state.get("audit_trail", [])
                    ),
                    error_audit,
                ],
                "context_data": {
                    **(
                        state.context_data
                        if hasattr(state, "context_data")
                        else state.get("context_data", {})
                    ),
                    "last_active_agent": "strategy_generator",
                    "error_message": "Missing requirements for strategy generation",
                },
            }
        )

    try:
        # Ensure state has EmailRequirements - create from context if needed
        if not state.email_requirements and requirements_data:
            # Convert legacy requirements format to EmailRequirements
            email_requirements = EmailRequirements(
                purpose=requirements_data.get("purpose", "General communication"),
                email_type="announcement",  # Default type
                audience=(
                    requirements_data.get("audience", ["team"])
                    if isinstance(requirements_data.get("audience"), list)
                    else [requirements_data.get("audience", "team")]
                ),
                tone=requirements_data.get("tone", "professional"),
                key_messages=(
                    requirements_data.get("key_messages", ["Key information"])
                    if isinstance(requirements_data.get("key_messages"), list)
                    else [requirements_data.get("key_messages", "Key information")]
                ),
                completeness_score=requirements_data.get("completeness_score", 0.8),
            )
            state = state.copy(update={"email_requirements": email_requirements})

        # Use StrategyGenerator for real AI-powered strategy generation
        generator = StrategyGenerationAgent()
        result_state = await generator.execute(state)

        execution_time = (datetime.now() - start_time).total_seconds()

        # Create audit entry for enterprise compliance
        success_audit = {
            "timestamp": datetime.now().isoformat(),
            "node": "strategy_generator",
            "action": "strategy_generated",
            "strategy_confidence": (
                result_state.email_strategy.confidence_score
                if result_state.email_strategy
                else 0.0
            ),
            "execution_time_ms": execution_time * 1000,
            "approach": (
                result_state.email_strategy.overall_approach
                if result_state.email_strategy
                else "unknown"
            ),
        }

        response_message = create_agent_message(
            "strategy_generator",
            "email_workflow_orchestrator",
            "Strategy generation complete",
            WorkflowPhase.STRATEGY_ANALYSIS,
            data=(
                result_state.email_strategy.model_dump()
                if result_state.email_strategy
                else {}
            ),
        )

        # Enhanced state update with component tracking
        updates = {
            "workflow_phase": WorkflowPhase.STRATEGY_CONFIRMATION,
            "messages": [
                *(
                    result_state.messages
                    if hasattr(result_state, "messages")
                    else result_state.get("messages", [])
                ),
                response_message,
            ],
            "component_outputs": {
                **(
                    result_state.component_outputs
                    if hasattr(result_state, "component_outputs")
                    else result_state.get("component_outputs", {})
                ),
                "strategy_generator": result_state.email_strategy,
            },
            "component_status": {
                **(
                    result_state.component_status
                    if hasattr(result_state, "component_status")
                    else result_state.get("component_status", {})
                ),
                "strategy_generator": "completed",
            },
            "audit_trail": [
                *(
                    result_state.audit_trail
                    if hasattr(result_state, "audit_trail")
                    else result_state.get("audit_trail", [])
                ),
                success_audit,
            ],
            "context_data": {
                **(
                    result_state.context_data
                    if hasattr(result_state, "context_data")
                    else result_state.get("context_data", {})
                ),
                "strategy_confidence": (
                    result_state.email_strategy.confidence_score
                    if result_state.email_strategy
                    else 0.0
                ),
                "last_active_agent": "strategy_generator",
                "generated_strategy": (
                    result_state.email_strategy.model_dump()
                    if result_state.email_strategy
                    else {}
                ),
            },
        }

        return result_state.copy(update=updates)

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        error_msg = f"Strategy generation failed: {e}"

        error_audit = {
            "timestamp": datetime.now().isoformat(),
            "node": "strategy_generator",
            "action": "generation_failed",
            "error": str(e),
            "execution_time_ms": execution_time * 1000,
        }

        msg = create_agent_message(
            "strategy_generator",
            "email_workflow_orchestrator",
            error_msg,
            WorkflowPhase.STRATEGY_ANALYSIS,
            data={"error": str(e)},
        )

        return state.copy(
            update={
                "messages": [
                    *(
                        state.messages
                        if hasattr(state, "messages")
                        else state.get("messages", [])
                    ),
                    msg,
                ],
                "component_status": {
                    **(
                        state.component_status
                        if hasattr(state, "component_status")
                        else state.get("component_status", {})
                    ),
                    "strategy_generator": "failed",
                },
                "audit_trail": [
                    *(
                        state.audit_trail
                        if hasattr(state, "audit_trail")
                        else state.get("audit_trail", [])
                    ),
                    error_audit,
                ],
                "context_data": {
                    **(
                        state.context_data
                        if hasattr(state, "context_data")
                        else state.get("context_data", {})
                    ),
                    "error_message": error_msg,
                    "last_active_agent": "strategy_generator",
                },
            }
        )


@streamlined_node("strategy_confirmation_handler", WorkflowPhase.STRATEGY_CONFIRMATION)
async def strategy_confirmation_handler(
    state: UniversalWorkflowState,
) -> UniversalWorkflowState:
    """Real strategy confirmation handler implementation with enhanced state management."""
    handler = StrategyConfirmationHandler()
    result_state = await handler.execute(state)

    # Ensure strategy is marked as confirmed if approved
    if result_state.email_strategy and (
        result_state.context_data
        if hasattr(result_state, "context_data")
        else result_state.get("context_data", {})
    ).get("strategy_approved"):
        confirmed_strategy = result_state.email_strategy.model_copy(
            update={"is_confirmed": True}
        )
        result_state = result_state.copy(update={"email_strategy": confirmed_strategy})

    # Add component tracking
    component_status = (
        "completed"
        if (
            result_state.context_data
            if hasattr(result_state, "context_data")
            else result_state.get("context_data", {})
        ).get("strategy_approved")
        else "pending"
    )

    return result_state.copy(
        update={
            "component_status": {
                **(
                    result_state.component_status
                    if hasattr(result_state, "component_status")
                    else result_state.get("component_status", {})
                ),
                "strategy_confirmation_handler": component_status,
            }
        }
    )


# NOTE: enhanced_email_generator is imported from nodes package
# The implementation in universal_framework.nodes.enhanced_email_generator
# provides comprehensive error handling, audit trails, component tracking,
