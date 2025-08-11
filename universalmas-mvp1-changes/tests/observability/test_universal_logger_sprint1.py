"""
Test suite for UniversalLogger - Sprint 1 Validation

Tests standard LangSmith patterns and production compatibility scenarios.
"""

import os
from unittest.mock import patch

# Import the new logger
try:
    from universal_framework.observability.langsmith_logger import (
        UniversalLogger,
        create_agent_logger,
        create_workflow_logger,
        setup_langsmith_environment,
    )
except ImportError:
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
    from universal_framework.observability.langsmith_logger import (
        UniversalLogger,
        create_agent_logger,
        create_workflow_logger,
        setup_langsmith_environment,
    )


class TestUniversalLogger:
    """Test suite for UniversalLogger core functionality"""

    def test_logger_initialization(self):
        """Test logger initializes without errors"""
        logger = UniversalLogger("test_component")
        assert logger.component_name == "test_component"
        assert logger.project == "universal-framework"
        assert logger.sampling_rate == 0.1

    def test_standard_logging_interface(self):
        """Test standard Python logging methods work - CRITICAL for production"""
        logger = UniversalLogger("test_component")

        # These calls must not raise AttributeError (was the original issue)
        logger.info("Test info message", extra_data="test")
        logger.error("Test error message", error_code=500)
        logger.warning("Test warning message", warning_type="config")
        logger.debug("Test debug message", debug_level="verbose")

        # Test with session_id (common production pattern)
        logger.info("Test with session", session_id="test_session_123")

    def test_production_scenarios(self):
        """Test the exact scenarios that were failing in production"""
        # Simulate intent_analyzer_chain.py line 67
        logger = UniversalLogger("intent_analyzer_chain")

        # These were the failing calls (lines 350, 381, 437)
        logger.info(
            "Processing intent analysis", session_id="sess_123", context="production"
        )
        logger.error(
            "Intent analysis failed", error_type="timeout", session_id="sess_123"
        )
        logger.warning("Intent analysis slow", duration_ms=2000, session_id="sess_123")

        # Test passes if no AttributeError raised
        assert True

    def test_enterprise_methods(self):
        """Test enterprise methods using @traceable patterns"""
        logger = UniversalLogger("test_component")

        # Test agent execution logging
        result = logger.log_agent_execution(
            agent_name="test_agent",
            session_id="test_session",
            success=True,
            execution_time_ms=150,
        )

        assert result["agent_name"] == "test_agent"
        assert result["success"] is True
        assert "session_id" in result
        assert result["component"] == "test_component"

    def test_workflow_transition_logging(self):
        """Test workflow transition tracing"""
        logger = UniversalLogger("workflow_test")

        result = logger.log_workflow_transition(
            from_phase="initialization", to_phase="discovery", duration_ms=200
        )

        assert result["from_phase"] == "initialization"
        assert result["to_phase"] == "discovery"
        assert result["transition"] == "initialization -> discovery"
        assert result["component"] == "workflow_test"

    def test_compliance_event_logging(self):
        """Test compliance event logging with tags"""
        logger = UniversalLogger("compliance_test")

        result = logger.log_compliance_event(
            event_type="data_processing",
            data_type="user_input",
            compliance_level="gdpr",
        )

        assert result["event_type"] == "data_processing"
        assert result["compliance_framework"] == "SOC2_ISO27001_GDPR"
        assert result["component"] == "compliance_test"

    def test_backward_compatibility(self):
        """Test backward compatibility with existing enterprise patterns"""
        logger = UniversalLogger("compat_test")

        # Test log_info method (used in existing code)
        logger.log_info(
            message="Test compatibility",
            session_id="test_session",
            context={"legacy": True},
        )

        # Test log_error method (used in existing code)
        logger.log_error(
            error_type="compatibility_test",
            error_message="Test error",
            session_id="test_session",
            context={"legacy": True},
        )

        # Test passes if no exceptions
        assert True

    def test_session_id_privacy(self):
        """Test session ID privacy protection"""
        logger = UniversalLogger("privacy_test")

        safe_id = logger._safe_session_id("very_long_session_id_with_sensitive_data")

        # Should be truncated to 8 chars + ***
        assert len(safe_id) == 11
        assert safe_id.endswith("***")
        assert safe_id.startswith("very_lon")

    def test_langsmith_environment_setup(self):
        """Test LangSmith environment configuration"""
        with patch.dict(os.environ, {}, clear=True):
            setup_langsmith_environment("test-project", "test-api-key")

            assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
            assert os.environ["LANGCHAIN_PROJECT"] == "test-project"
            assert os.environ["LANGCHAIN_API_KEY"] == "test-api-key"
            assert "langchain.com" in os.environ["LANGCHAIN_ENDPOINT"]

    def test_factory_methods(self):
        """Test factory methods for common use cases"""
        agent_logger = create_agent_logger("test_agent")
        assert agent_logger.component_name == "agent_test_agent"

        workflow_logger = create_workflow_logger()
        assert workflow_logger.component_name == "workflow_orchestrator"

    def test_langsmith_unavailable_fallback(self):
        """Test fallback behavior when LangSmith is unavailable"""
        with patch(
            "universal_framework.observability.langsmith_logger.LANGSMITH_AVAILABLE",
            False,
        ):
            logger = UniversalLogger("fallback_test")

            # Should still work without LangSmith
            logger.info("Fallback test")
            result = logger.log_agent_execution("test_agent", "test_session")

            assert result["agent_name"] == "test_agent"
            assert not logger.langsmith_available

    def test_performance_logging(self):
        """Test performance metric logging"""
        logger = UniversalLogger("perf_test")

        logger.log_performance_metric(
            metric_name="response_time", metric_value=125.5, endpoint="/api/workflow"
        )

        # Test passes if no exceptions
        assert True

    def test_initialization_logging(self):
        """Test component initialization logging"""
        logger = UniversalLogger("init_test")

        logger.log_initialization(
            message="Component started successfully",
            version="3.1.0",
            config_loaded=True,
        )

        # Test passes if no exceptions
        assert True


class TestProductionCompatibility:
    """Test specific production scenarios that were failing"""

    def test_intent_analyzer_chain_scenario(self):
        """Test exact scenario from intent_analyzer_chain.py"""
        # Line 67: logger = UniversalFrameworkLogger("intent_analyzer_chain")
        logger = UniversalLogger("intent_analyzer_chain")

        # Lines 350, 381, 437: logger.info() calls
        logger.info("Intent analysis started", session_id="prod_session")
        logger.info("Context loaded", context_size=1500)
        logger.info("Analysis complete", confidence=0.85)

        # Must not raise AttributeError
        assert True

    def test_intent_classifier_scenario(self):
        """Test exact scenario from intent_classifier.py"""
        logger = UniversalLogger("intent_classifier")

        # Multiple logger.info() calls from production
        logger.info("Classification started")
        logger.error("Classification failed", error="timeout")
        logger.warning("Low confidence", confidence=0.4)

        # Must not raise AttributeError
        assert True

    def test_workflow_api_scenario(self):
        """Test API endpoint logging scenarios"""
        logger = UniversalLogger("api_workflow")

        # Common API logging patterns
        logger.info("Request received", method="POST", endpoint="/workflow")
        logger.error("Request failed", status_code=500, error="internal")
        logger.warning("Slow response", response_time_ms=3000)

        # Must not raise AttributeError
        assert True


class TestLangSmithIntegration:
    """Test LangSmith-specific functionality"""

    def test_traceable_decorator_fallback(self):
        """Test @traceable decorator works with fallback"""
        logger = UniversalLogger("trace_test")

        # These methods use @traceable decorator
        result1 = logger.log_agent_execution("test_agent", "test_session")
        result2 = logger.log_workflow_transition("init", "discovery")
        result3 = logger.log_compliance_event("audit_event")

        # Should return proper results even without LangSmith
        assert result1["agent_name"] == "test_agent"
        assert result2["from_phase"] == "init"
        assert result3["event_type"] == "audit_event"

    @patch(
        "universal_framework.observability.langsmith_logger.LANGSMITH_AVAILABLE", True
    )
    def test_langsmith_client_initialization(self):
        """Test LangSmith client setup when available"""
        with patch.dict(os.environ, {"LANGCHAIN_API_KEY": "test-key"}):
            logger = UniversalLogger("langsmith_test")

            # Should attempt to create LangSmith client
            assert hasattr(logger, "langsmith_client")


# Sprint 1 validation function
def run_sprint1_validation():
    """
    Sprint 1 validation - tests all critical functionality

    Returns: (success: bool, issues: List[str])
    """
    issues = []

    try:
        # Test 1: Basic initialization
        logger = UniversalLogger("validation_test")

        # Test 2: Standard logging interface (CRITICAL)
        logger.info("Validation test")
        logger.error("Validation error")
        logger.warning("Validation warning")

        # Test 3: Production scenarios
        logger.info("Production test", session_id="val_session")

        # Test 4: Enterprise methods
        logger.log_agent_execution("val_agent", "val_session")
        logger.log_workflow_transition("init", "discovery")
        logger.log_compliance_event("validation")

        print("✅ Sprint 1 validation PASSED")
        return True, []

    except Exception as e:
        issues.append(f"Sprint 1 validation failed: {e}")
        print(f"❌ Sprint 1 validation FAILED: {e}")
        return False, issues


if __name__ == "__main__":
    # Run validation when script executed directly
    success, issues = run_sprint1_validation()
    exit(0 if success else 1)
