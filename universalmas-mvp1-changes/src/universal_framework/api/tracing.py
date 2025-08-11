"""OpenTelemetry tracing utilities."""

from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase

# Make agent execution logging optional
try:
    from universal_framework.observability.agent_execution_logger import (
        AgentExecutionLogger,
    )

    _agent_logging_available = True
except ImportError:
    _agent_logging_available = False


def setup_opentelemetry(app: Any) -> trace.Tracer:
    """Configure OpenTelemetry for the FastAPI app."""
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        span_processor = BatchSpanProcessor(exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)  # type: ignore[attr-defined]

    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()
    return tracer


async def execute_workflow_with_tracing(
    workflow: Any,
    initial_state: UniversalWorkflowState,
    session_id: str,
) -> UniversalWorkflowState:
    """Execute workflow with an OpenTelemetry span."""
    import time

    tracer = trace.get_tracer(__name__)
    workflow_start_time = time.perf_counter()

    with tracer.start_as_current_span("workflow_execution") as span:
        span.set_attribute("workflow.session_id", session_id)
        # Defensive programming for workflow_phase access
        try:
            initial_phase = initial_state.workflow_phase
        except AttributeError:
            initial_phase = WorkflowPhase(
                initial_state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
            )
        span.set_attribute("workflow.phase", initial_phase.value)
        span.set_attribute("workflow.user_id", initial_state.user_id)

        # Enhanced config following LangGraph best practices
        config = {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": "",  # Required for proper checkpointer operation
            },
            "recursion_limit": 200,  # Increased recursion limit to match graph configuration
        }

        # Log workflow start
        if _agent_logging_available:
            try:
                execution_logger = AgentExecutionLogger()
                execution_logger.log_agent_execution(
                    session_id=session_id,
                    agent_name="workflow_engine",
                    agent_response={
                        "status": "workflow_started",
                        "initial_phase": initial_phase.value,
                        "user_id": initial_state.user_id,
                    },
                    rationale=f"Starting workflow execution from phase {initial_phase.value} for user {initial_state.user_id}",
                    prompt_template="Workflow orchestration and state management",
                    input_data={
                        "initial_phase": initial_phase.value,
                        "user_id": initial_state.user_id,
                        "config": config,
                        "recursion_limit": config.get("recursion_limit", 200),
                    },
                    workflow_phase="WORKFLOW_START",
                )
            except Exception as e:
                # Log the error but don't break the workflow
                from ..core.logging_foundation import get_safe_logger

                logger = get_safe_logger("tracing")
                logger.warning(
                    "workflow_start_logging_failed", error=str(e), session_id=session_id
                )
            pass

        try:
            result_state: UniversalWorkflowState = await workflow.ainvoke(
                initial_state,
                config=config,
            )

            # Calculate total execution time
            workflow_execution_time_ms = (
                time.perf_counter() - workflow_start_time
            ) * 1000

            # Defensive programming for workflow_phase access
            try:
                final_phase = result_state.workflow_phase
            except AttributeError:
                final_phase = WorkflowPhase(
                    result_state.get(
                        "workflow_phase", WorkflowPhase.INITIALIZATION.value
                    )
                )
            span.set_attribute("workflow.final_phase", final_phase.value)

            # Log workflow completion
            if _agent_logging_available:
                try:
                    execution_logger = AgentExecutionLogger()
                    execution_logger.log_agent_execution(
                        session_id=session_id,
                        agent_name="workflow_engine",
                        agent_response={
                            "status": "workflow_completed",
                            "initial_phase": initial_phase.value,
                            "final_phase": final_phase.value,
                            "phase_transition": f"{initial_phase.value} -> {final_phase.value}",
                            "completion_percentage": (
                                getattr(result_state, "phase_completion", {}).get(
                                    final_phase, 0.0
                                )
                                if hasattr(result_state, "phase_completion")
                                else result_state.get("phase_completion", {}).get(
                                    final_phase, 0.0
                                )
                            ),
                        },
                        rationale=f"Successfully completed workflow execution, transitioned from {initial_phase.value} to {final_phase.value}",
                        prompt_template="Workflow orchestration and state management",
                        input_data={
                            "initial_phase": initial_phase.value,
                            "final_phase": final_phase.value,
                            "workflow_duration_ms": workflow_execution_time_ms,
                        },
                        execution_time_ms=workflow_execution_time_ms,
                        workflow_phase=final_phase.value,
                    )
                except Exception as e:
                    # Log the error but don't break the workflow
                    from ..core.logging_foundation import (
                        get_safe_logger,
                    )

                    logger = get_safe_logger("tracing")
                    logger.warning(
                        "workflow_completion_logging_failed",
                        error=str(e),
                        session_id=session_id,
                    )

            return result_state

        except Exception as workflow_error:
            # Calculate execution time for failed workflow
            workflow_execution_time_ms = (
                time.perf_counter() - workflow_start_time
            ) * 1000

            # Log workflow failure
            if _agent_logging_available:
                try:
                    execution_logger = AgentExecutionLogger()
                    execution_logger.log_agent_execution(
                        session_id=session_id,
                        agent_name="workflow_engine",
                        agent_response={
                            "status": "workflow_failed",
                            "error_type": type(workflow_error).__name__,
                            "error_message": str(workflow_error),
                        },
                        rationale=f"Workflow execution failed: {str(workflow_error)}",
                        prompt_template="Workflow orchestration and state management",
                        input_data={
                            "initial_phase": initial_phase.value,
                            "error_occurred_at_ms": workflow_execution_time_ms,
                            "error_type": type(workflow_error).__name__,
                        },
                        execution_time_ms=workflow_execution_time_ms,
                        success=False,
                        error_message=str(workflow_error),
                        workflow_phase="WORKFLOW_ERROR",
                    )
                except Exception as e:
                    # Log the error but don't break the workflow
                    from ..core.logging_foundation import (
                        get_safe_logger,
                    )

                    logger = get_safe_logger("tracing")
                    logger.warning(
                        "workflow_failure_logging_failed",
                        error=str(e),
                        session_id=session_id,
                    )

            raise
