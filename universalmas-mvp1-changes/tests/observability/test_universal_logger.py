"""
Comprehensive tests for UniversalLogger
Tests both standard interface and enterprise features
"""

from unittest.mock import patch

import pytest

from universal_framework.observability.universal_logger import UniversalLogger


class TestUniversalLoggerBasics:
    """Test basic logging functionality"""

    @pytest.fixture
    def logger(self):
        return UniversalLogger("test_component")

    def test_standard_logging_interface(self, logger):
        """Test that standard Python logging methods work"""
        # These should not raise AttributeError
        logger.info("Test info message")
        logger.error("Test error message")
        logger.warning("Test warning message")
    logger.info("Test debug message")

    def test_enterprise_logging_methods(self, logger):
        """Test enterprise-specific logging methods"""
        logger.log_agent_execution("test_agent", "session123", success=True)
        logger.log_workflow_transition("init", "discovery", "session123")
        logger.log_compliance_event("test_event", session_id="session123")

    def test_backwards_compatibility(self, logger):
        """Test that this logger can replace UniversalFrameworkLogger"""
        # Test backward compatibility methods
        logger.log_info(
            "Test message", session_id="session123", context={"key": "value"}
        )
        logger.log_error("validation_error", "Test error", session_id="session123")
        logger.log_warning("Test warning", session_id="session123")

    def test_production_scenario_fix(self, logger):
        """Test the exact scenario that was failing in production"""
        # Simulate the failing production scenario from intent_analyzer_chain.py
        logger.info("Agent analysis complete", session_id="test_session")
        logger.error(
            "Processing failed", error_type="validation", session_id="test_session"
        )
        logger.warning("Performance threshold exceeded", duration_ms=100)


class TestLangSmithIntegration:
    """Test LangSmith integration with fallbacks"""

    def test_langsmith_unavailable_graceful_fallback(self):
        """Test graceful fallback when LangSmith unavailable"""
        with patch(
            "universal_framework.observability.universal_logger.LANGSMITH_AVAILABLE",
            False,
        ):
            logger = UniversalLogger("test_component")
            assert not logger.langsmith_enabled
            # Should still work for basic logging
            logger.info("Test message")

    @patch("universal_framework.observability.universal_logger.LangSmithClient")
    def test_langsmith_configuration_error_fallback(self, mock_client):
        """Test fallback when LangSmith config fails"""
        mock_client.side_effect = Exception("Config failed")
        logger = UniversalLogger("test_component")
        assert not logger.langsmith_enabled
        logger.info("Test message")

    @patch(
        "universal_framework.observability.universal_logger.LANGSMITH_AVAILABLE", True
    )
    @patch("universal_framework.observability.universal_logger.LangSmithClient")
    @patch("universal_framework.observability.universal_logger.LangChainTracer")
    def test_langsmith_successful_integration(self, mock_tracer, mock_client):
        """Test successful LangSmith integration"""
        logger = UniversalLogger("test_component")
        assert logger.langsmith_enabled
        mock_client.assert_called_once()
        mock_tracer.assert_called_once()


class TestPerformanceAndSampling:
    """Test performance monitoring and sampling"""

    def test_sampling_respects_rate(self):
        """Test that sampling works correctly"""
        logger = UniversalLogger("test_component", sampling_rate=0.0)  # No sampling
        with patch.object(logger.structlog_logger, "info") as mock_log:
            logger.info("Test message")
            mock_log.assert_not_called()  # Should be sampled out

    def test_compliance_events_never_sampled(self):
        """Test that compliance events are always logged"""
        logger = UniversalLogger("test_component", sampling_rate=0.0)
        with patch.object(logger.structlog_logger, "info") as mock_log:
            logger.log_compliance_event("test_event")
            mock_log.assert_called_once()  # Should never be sampled

    def test_full_sampling_always_logs(self):
        """Test that 100% sampling always logs"""
        logger = UniversalLogger("test_component", sampling_rate=1.0)
        with patch.object(logger.structlog_logger, "info") as mock_log:
            logger.info("Test message")
            mock_log.assert_called_once()


class TestPrivacyAndSecurity:
    """Test privacy protection and session ID hashing"""

    def test_session_id_hashing(self):
        """Test that session IDs are hashed for privacy"""
        logger = UniversalLogger("test_component", sampling_rate=1.0)
        with patch.object(
            logger.privacy_logger,
            "_safe_hash_session_id",
            return_value="hashed_session",
        ) as mock_hash:
            with patch.object(logger.structlog_logger, "info") as mock_log:
                logger.info("Test message", session_id="sensitive_session_123")
                mock_hash.assert_called_once_with("sensitive_session_123")
                # Verify the logged data contains hashed session, not original
                call_args = mock_log.call_args
                assert "session_hash" in call_args[1]
                assert "session_id" not in call_args[1]

    def test_pii_redaction(self):
        """Test that PII is redacted from logs"""
        logger = UniversalLogger("test_component", sampling_rate=1.0)
        with patch.object(
            logger.privacy_logger, "redact_pii", return_value={"safe": "data"}
        ) as mock_redact:
            with patch.object(logger.structlog_logger, "info") as mock_log:
                logger.info("Test message", email="user@example.com", ssn="123-45-6789")
                mock_redact.assert_called_once()
                # Verify original PII not in final log call
                call_args = mock_log.call_args[1]
                assert "email" not in call_args
                assert "ssn" not in call_args


class TestPerformanceMonitoring:
    """Test performance monitoring features"""

    def test_performance_threshold_monitoring(self):
        """Test that performance violations are detected"""
        logger = UniversalLogger("test_component", sampling_rate=1.0)
        logger._performance_threshold_ms = 0.001  # Very low threshold for testing

        with patch.object(logger.structlog_logger, "warning") as mock_warning:
            with patch("time.perf_counter", side_effect=[0.0, 0.01]):  # 10ms delay
                logger.info("Slow log message")
                mock_warning.assert_called_once()
                call_args = mock_warning.call_args[1]
                assert "logging_performance_violation" in mock_warning.call_args[0]
                assert "overhead_ms" in call_args


class TestComponentInitialization:
    """Test logger initialization and configuration"""

    def test_component_name_binding(self):
        """Test that component name is properly bound"""
        logger = UniversalLogger("test_component_name")
        assert logger.component_name == "test_component_name"
        # Verify component name is bound to structlog logger
        assert (
            logger.structlog_logger._context["framework_component"]
            == "test_component_name"
        )

    def test_custom_sampling_rate(self):
        """Test custom sampling rate configuration"""
        logger = UniversalLogger("test_component", sampling_rate=0.5)
        assert logger.sampling_rate == 0.5

    def test_custom_langsmith_project(self):
        """Test custom LangSmith project configuration"""
        with patch(
            "universal_framework.observability.universal_logger.LANGSMITH_AVAILABLE",
            False,
        ):
            logger = UniversalLogger(
                "test_component", langsmith_project="custom-project"
            )
            # Even with fallback, the project name should be stored
