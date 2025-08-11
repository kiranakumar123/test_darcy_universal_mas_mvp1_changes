"""
Agent Execution Logger - Comprehensive Backend Logging for All Agent Executions
==============================================================================

This module provides detailed backend logging for every agent execution in the
Universal Multi-Agent System Framework. It captures session_id, timestamp, source,
response, rationale, prompt template, and input data for complete observability.

Designed to work seamlessly with the existing clean frontend/backend separation
without impacting user-facing API responses.
"""

import json
from datetime import datetime
from typing import Any

from ..core.logging_foundation import get_safe_logger

# Privacy logging now handled via dependency injection


class AgentExecutionLogger:
    """
    Comprehensive backend logging for all agent executions.

    Captures detailed execution information for debugging, monitoring,
    and compliance while maintaining clean frontend responses.
    """

    def __init__(self, component_name: str = "agent_execution_logger"):
        """Initialize the agent execution logger."""
        self.logger = get_safe_logger(component_name)
        self.component_name = component_name

        # Initialize privacy logger for backward compatibility
        try:
            from ..compliance.privacy_logger import PrivacySafeLogger

            self.privacy_logger = PrivacySafeLogger()
        except ImportError:
            # Create a mock privacy logger if not available
            class MockPrivacyLogger:
                def log_agent_execution(self, **kwargs):
                    """Mock implementation for testing/fallback."""
                    pass

            self.privacy_logger = MockPrivacyLogger()

    def log_agent_execution(
        self,
        session_id: str,
        agent_name: str,
        agent_response: dict[str, Any] | str | Any,
        rationale: str | None = None,
        prompt_template: str | None = None,
        input_data: dict[str, Any] | None = None,
        execution_time_ms: float | None = None,
        success: bool = True,
        error_message: str | None = None,
        workflow_phase: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> None:
        """
        Log comprehensive agent execution details.

        Args:
            session_id: Session identifier for tracking
            agent_name: Name/type of the agent that executed
            agent_response: The actual response produced by the agent
            rationale: Agent's internal reasoning for the response
            prompt_template: The prompt template used to generate the response
            input_data: Input data provided to the agent
            execution_time_ms: Execution time in milliseconds
            success: Whether the execution was successful
            error_message: Error message if execution failed
            workflow_phase: Current workflow phase during execution
            additional_context: Any additional context information
        """
        timestamp = datetime.now().isoformat()

        # Extract user-facing message from agent response
        user_message = self._extract_user_message(agent_response)

        # Prepare comprehensive log data
        log_data = {
            "event_type": "agent_execution_comprehensive",
            "timestamp": timestamp,
            "session_id": session_id,
            "agent_name": agent_name,
            "workflow_phase": workflow_phase,
            "execution_time_ms": execution_time_ms,
            "success": success,
            # Core execution details
            "agent_response": self._serialize_response(agent_response),
            "user_message_extracted": user_message,
            "rationale": rationale,
            "prompt_template": prompt_template,
            "input_data": self._redact_sensitive_data(input_data),
            # Error handling
            "error_message": error_message,
            # Additional context
            "additional_context": additional_context or {},
            # Metadata
            "logged_by": self.component_name,
            "privacy_compliant": True,
        }

        # Remove None values for cleaner logs
        log_data = {k: v for k, v in log_data.items() if v is not None}

        # Log using structured logger
        if success:
            self.logger.info("agent_execution_comprehensive", **log_data)
        else:
            self.logger.error("agent_execution_failure", **log_data)

        # Also log to privacy-safe logger for compliance
        try:
            self.privacy_logger.log_agent_execution(
                agent_name=agent_name,
                session_id=session_id,
                execution_context={
                    "workflow_phase": workflow_phase,
                    "rationale": rationale,
                    "prompt_template": prompt_template,
                    "user_message": user_message,
                    "execution_time_ms": execution_time_ms,
                    **(additional_context or {}),
                },
                performance_metrics={"execution_time_ms": execution_time_ms or 0},
                success=success,
                error_message=error_message,
            )
        except Exception as e:
            # Fallback logging if privacy logger fails
            self.logger.warning(
                "privacy_logger_fallback",
                session_id=session_id[:8] + "..." if session_id else "unknown",
                agent_name=agent_name,
                fallback_reason=str(e),
            )

    def log_intent_classification(
        self,
        session_id: str,
        user_input: str,
        classified_intent: str,
        confidence_score: float | None = None,
        execution_time_ms: float | None = None,
        capabilities_response: str | None = None,
    ) -> None:
        """
        Log intent classification specifically.

        Args:
            session_id: Session identifier
            user_input: Original user input
            classified_intent: The classified intent
            confidence_score: Classification confidence (if available)
            execution_time_ms: Classification time
            capabilities_response: Response provided for help requests
        """
        self.log_agent_execution(
            session_id=session_id,
            agent_name="intent_classifier",
            agent_response={
                "intent": classified_intent,
                "confidence": confidence_score,
                "capabilities_response": capabilities_response,
            },
            rationale=f"Classified user input as '{classified_intent}' based on pattern matching and help detection",
            prompt_template="Intent classification using regex patterns and help keywords",
            input_data={"user_input": user_input},
            execution_time_ms=execution_time_ms,
            workflow_phase="initialization",
            additional_context={
                "classification_type": "rule_based",
                "help_keywords_detected": any(
                    keyword in user_input.lower()
                    for keyword in [
                        "help",
                        "assist",
                        "support",
                        "can you",
                        "what can",
                        "how can",
                    ]
                ),
            },
        )

    def log_workflow_agent_execution(
        self,
        session_id: str,
        agent_name: str,
        state_input: dict[str, Any],
        state_output: dict[str, Any],
        rationale: str | None = None,
        prompt_template: str | None = None,
        execution_time_ms: float | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """
        Log workflow agent execution with state transitions.

        Args:
            session_id: Session identifier
            agent_name: Name of the workflow agent
            state_input: Input state provided to agent
            state_output: Output state from agent
            rationale: Agent's reasoning process
            prompt_template: Template used for generation
            execution_time_ms: Execution time
            success: Execution success status
            error_message: Error details if failed
        """
        # Extract workflow phase from state
        workflow_phase = self._extract_workflow_phase(state_input, state_output)

        # Extract user-relevant changes
        state_changes = self._analyze_state_changes(state_input, state_output)

        self.log_agent_execution(
            session_id=session_id,
            agent_name=agent_name,
            agent_response=state_changes,
            rationale=rationale,
            prompt_template=prompt_template,
            input_data={
                "workflow_phase": workflow_phase,
                "state_keys": (
                    list(state_input.keys()) if isinstance(state_input, dict) else []
                ),
                "input_message_count": (
                    len(state_input.get("messages", []))
                    if isinstance(state_input, dict)
                    else 0
                ),
            },
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
            workflow_phase=workflow_phase,
            additional_context={
                "state_transition": True,
                "output_keys": (
                    list(state_output.keys()) if isinstance(state_output, dict) else []
                ),
                "output_message_count": (
                    len(state_output.get("messages", []))
                    if isinstance(state_output, dict)
                    else 0
                ),
            },
        )

    def _extract_user_message(self, agent_response: Any) -> str | None:
        """Extract user-facing message from agent response."""
        if isinstance(agent_response, str):
            return agent_response
        elif isinstance(agent_response, dict):
            # Try multiple keys for user message
            for key in ["message", "response", "content", "text", "output"]:
                if key in agent_response:
                    return str(agent_response[key])
            # If no direct message, try to extract from nested structures
            if "data" in agent_response and isinstance(agent_response["data"], dict):
                return self._extract_user_message(agent_response["data"])
        return None

    def _serialize_response(self, response: Any) -> Any:
        """Serialize response for logging, handling complex objects."""
        try:
            if isinstance(response, str | int | float | bool | type(None)):
                return response
            elif isinstance(response, dict | list):
                return json.loads(json.dumps(response, default=str))
            else:
                return str(response)
        except Exception:
            return str(response)

    def _redact_sensitive_data(
        self, data: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Redact sensitive data from input data."""
        if not data:
            return data

        redacted_data = {}
        sensitive_keys = {"password", "token", "secret", "key", "auth", "credential"}

        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                redacted_data[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted_data[key] = self._redact_sensitive_data(value)
            else:
                redacted_data[key] = value

        return redacted_data

    def _extract_workflow_phase(
        self, state_input: dict[str, Any], state_output: dict[str, Any]
    ) -> str | None:
        """Extract workflow phase from state objects."""
        # Try output first, then input
        for state in [state_output, state_input]:
            if isinstance(state, dict):
                if hasattr(state, "workflow_phase"):
                    return str(state.workflow_phase)
                elif "workflow_phase" in state:
                    return str(state["workflow_phase"])
        return None

    def _analyze_state_changes(
        self, state_input: dict[str, Any], state_output: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze what changed between input and output states."""
        changes = {
            "input_keys": (
                list(state_input.keys()) if isinstance(state_input, dict) else []
            ),
            "output_keys": (
                list(state_output.keys()) if isinstance(state_output, dict) else []
            ),
        }

        if isinstance(state_input, dict) and isinstance(state_output, dict):
            # Check for new keys added
            new_keys = set(state_output.keys()) - set(state_input.keys())
            if new_keys:
                changes["new_keys_added"] = list(new_keys)

            # Check for message changes
            input_messages = state_input.get("messages", [])
            output_messages = state_output.get("messages", [])
            if len(output_messages) > len(input_messages):
                changes["new_messages_added"] = len(output_messages) - len(
                    input_messages
                )

        return changes


# Global logger instance
agent_execution_logger = AgentExecutionLogger()


# Convenience functions for common use cases
def log_agent_execution(
    session_id: str,
    agent_name: str,
    agent_response: dict[str, Any] | str | Any,
    rationale: str | None = None,
    prompt_template: str | None = None,
    input_data: dict[str, Any] | None = None,
    execution_time_ms: float | None = None,
    success: bool = True,
    error_message: str | None = None,
    workflow_phase: str | None = None,
    additional_context: dict[str, Any] | None = None,
) -> None:
    """Convenience function for logging agent execution."""
    agent_execution_logger.log_agent_execution(
        session_id=session_id,
        agent_name=agent_name,
        agent_response=agent_response,
        rationale=rationale,
        prompt_template=prompt_template,
        input_data=input_data,
        execution_time_ms=execution_time_ms,
        success=success,
        error_message=error_message,
        workflow_phase=workflow_phase,
        additional_context=additional_context,
    )


def log_intent_classification(
    session_id: str,
    user_input: str,
    classified_intent: str,
    confidence_score: float | None = None,
    execution_time_ms: float | None = None,
    capabilities_response: str | None = None,
) -> None:
    """Convenience function for logging intent classification."""
    agent_execution_logger.log_intent_classification(
        session_id=session_id,
        user_input=user_input,
        classified_intent=classified_intent,
        confidence_score=confidence_score,
        execution_time_ms=execution_time_ms,
        capabilities_response=capabilities_response,
    )


def log_workflow_agent_execution(
    session_id: str,
    agent_name: str,
    state_input: dict[str, Any],
    state_output: dict[str, Any],
    rationale: str | None = None,
    prompt_template: str | None = None,
    execution_time_ms: float | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    """Convenience function for logging workflow agent execution."""
    agent_execution_logger.log_workflow_agent_execution(
        session_id=session_id,
        agent_name=agent_name,
        state_input=state_input,
        state_output=state_output,
        rationale=rationale,
        prompt_template=prompt_template,
        execution_time_ms=execution_time_ms,
        success=success,
        error_message=error_message,
    )
