"""
Comprehensive tests for Universal Framework exception hierarchy
Tests all custom exceptions with contextual metadata
"""

from datetime import datetime

from src.universal_framework.contracts.exceptions import (
    AgentExecutionError,
    APIValidationError,
    ConfigurationError,
    StateValidationError,
    UniversalFrameworkError,
    WorkflowValidationError,
)


class TestUniversalFrameworkError:
    """Test base exception class with enterprise context"""

    def test_basic_exception_creation(self):
        error = UniversalFrameworkError("Test error message")
        assert error.message == "Test error message"
        assert error.context == {}
        assert error.session_id is None
        assert error.agent_name is None
        assert isinstance(error.timestamp, str)

    def test_exception_with_full_context(self):
        context = {"key": "value", "number": 42}
        error = UniversalFrameworkError(
            message="Test error with context",
            context=context,
            session_id="test-session-123",
            agent_name="test_agent",
        )
        assert error.message == "Test error with context"
        assert error.context == context
        assert error.session_id == "test-session-123"
        assert error.agent_name == "test_agent"

    def test_exception_to_dict_conversion(self):
        error = UniversalFrameworkError(
            message="Serialization test",
            context={"test": True},
            session_id="session-456",
        )
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "UniversalFrameworkError"
        assert error_dict["message"] == "Serialization test"
        assert error_dict["context"]["test"] is True
        assert error_dict["session_id"] == "session-456"
        assert "timestamp" in error_dict
        assert "stack_trace" in error_dict


class TestAgentExecutionError:
    """Test agent-specific exception with execution context"""

    def test_agent_execution_error_creation(self):
        error = AgentExecutionError(
            message="LLM timeout",
            agent_name="requirements_collector",
            execution_phase="llm_call",
            session_id="session-789",
        )
        assert "Agent 'requirements_collector' execution failed" in str(error)
        assert error.agent_name == "requirements_collector"
        assert error.execution_phase == "llm_call"
        assert error.context["execution_phase"] == "llm_call"
        assert error.context["agent_type"] == "universal_agent"


class TestStateValidationError:
    """Test state validation with field-specific context"""

    def test_state_validation_error_creation(self):
        error = StateValidationError(
            message="Required field missing",
            field_name="user_objective",
            current_phase="discovery",
            expected_value="non-empty string",
            actual_value=None,
            session_id="session-abc",
        )
        assert "State validation failed" in str(error)
        assert error.field_name == "user_objective"
        assert error.current_phase == "discovery"
        assert error.context["field_name"] == "user_objective"
        assert error.context["current_phase"] == "discovery"


class TestWorkflowValidationError:
    """Test workflow and FSM validation"""

    def test_workflow_validation_error_creation(self):
        error = WorkflowValidationError(
            message="Invalid phase transition",
            current_phase="initialization",
            target_phase="generation",
            workflow_type="email_generation",
        )
        assert "Workflow validation failed" in str(error)
        assert error.context["current_phase"] == "initialization"
        assert error.context["target_phase"] == "generation"
        assert error.context["workflow_type"] == "email_generation"


class TestAPIValidationError:
    """Test API request validation"""

    def test_api_validation_error_creation(self):
        error = APIValidationError(
            message="Invalid parameter value",
            endpoint="/api/workflow/create",
            parameter="workflow_type",
            session_id="api-session-123",
        )
        assert "API validation failed" in str(error)
        assert error.context["endpoint"] == "/api/workflow/create"
        assert error.context["parameter"] == "workflow_type"


class TestConfigurationError:
    """Test configuration validation"""

    def test_configuration_error_creation(self):
        error = ConfigurationError(
            message="Missing required configuration",
            config_section="llm",
            config_key="api_key",
        )
        assert "Configuration error" in str(error)
        assert error.context["config_section"] == "llm"
        assert error.context["config_key"] == "api_key"


class TestExceptionIntegration:
    """Test exception integration with existing systems"""

    def test_exception_audit_trail_integration(self):
        error = AgentExecutionError(
            message="Integration test",
            agent_name="test_agent",
            session_id="audit-test-123",
        )
        error_dict = error.to_dict()
        assert "session_id" in error_dict
        assert "agent_name" in error_dict
        assert "timestamp" in error_dict
        datetime.fromisoformat(error_dict["timestamp"])

    def test_exception_enterprise_monitoring_format(self):
        error = StateValidationError(
            message="Enterprise monitoring test",
            field_name="test_field",
            current_phase="test_phase",
        )
        error_dict = error.to_dict()
        required_fields = ["error_type", "message", "context", "timestamp"]
        for field in required_fields:
            assert field in error_dict
        assert isinstance(error_dict["context"], dict)
        assert "validation_type" in error_dict["context"]
