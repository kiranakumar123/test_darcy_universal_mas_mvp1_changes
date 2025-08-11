"""Tests for LangSmith-first EnterpriseAuditManager."""

import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from universal_framework.compliance import (
    ComplianceError,
    PrivacySafeLogger,
    StateValidationError,
)
from universal_framework.observability import (
    EnterpriseAuditManager,
    EnterpriseLangSmithConfig,
)


@pytest.fixture
def mock_langsmith_config():
    """Create a mock LangSmith configuration for testing."""
    config = MagicMock(spec=EnterpriseLangSmithConfig)
    config.pii_detector = MagicMock()
    config.pii_detector.hash_session_id.return_value = "hashed_session_123"
    config.create_privacy_safe_trace_metadata.return_value = {
        "session_hash": "hashed_session_123",
        "agent_name": "test_agent",
        "project_name": "universal-framework",
    }
    config.circuit_breaker = MagicMock()
    config.circuit_breaker.state = "CLOSED"
    config.circuit_breaker.failure_count = 0
    config.circuit_breaker.failure_threshold = 5
    config.circuit_breaker.__aenter__ = AsyncMock(return_value=config.circuit_breaker)
    config.circuit_breaker.__aexit__ = AsyncMock(return_value=None)
    config.enterprise_settings = {"max_trace_overhead_ms": 10.0}
    return config


@pytest.fixture
def mock_privacy_logger():
    """Create a mock privacy logger for testing."""
    logger = MagicMock(spec=PrivacySafeLogger)
    logger.log_agent_execution = MagicMock()
    return logger


@pytest.fixture
def enterprise_audit_manager(mock_privacy_logger, mock_langsmith_config):
    """Create an EnterpriseAuditManager for testing."""
    return EnterpriseAuditManager(
        privacy_logger=mock_privacy_logger,
        langsmith_config=mock_langsmith_config,
        hash_salt="test_salt",
    )


class TestEnterpriseAuditManagerLangSmithIntegration:
    """Test LangSmith integration in EnterpriseAuditManager."""

    @pytest.mark.asyncio
    async def test_log_operation_with_langsmith_tracing(
        self, enterprise_audit_manager, mock_langsmith_config
    ):
        """Test that log_operation includes LangSmith tracing and correlation."""
        with patch(
            "universal_framework.observability.enterprise_audit.CrossPlatformTraceCorrelator"
        ) as mock_correlator_class:
            mock_correlator = MagicMock()
            mock_correlator.get_current_trace_context.return_value = {
                "session_hash": "hashed_session_123",
                "opentelemetry": {"trace_id": "test_trace_id"},
                "correlation_timestamp": time.time(),
            }
            mock_correlator_class.return_value = mock_correlator
            enterprise_audit_manager.trace_correlator = mock_correlator

            # Mock the enterprise system logging
            with (
                patch.object(
                    enterprise_audit_manager, "_log_to_enterprise_system_with_langsmith"
                ) as mock_log_enterprise,
                patch.object(
                    enterprise_audit_manager, "_attribute_audit_cost"
                ) as mock_cost,
            ):

                audit_id = await enterprise_audit_manager.log_operation(
                    "test_operation", "session_123", {"test": "metadata"}
                )

                # Verify audit ID is generated
                assert audit_id.startswith("audit_")
                assert audit_id in enterprise_audit_manager.audit_registry

                # Verify LangSmith trace metadata is included
                record = enterprise_audit_manager.audit_registry[audit_id]
                assert "trace_metadata" in record
                assert "correlation_context" in record
                assert record["trace_metadata"]["session_hash"] == "hashed_session_123"

                # Verify enterprise logging was called
                mock_log_enterprise.assert_called_once()
                mock_cost.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_agent_execution_with_langsmith_decorators(
        self, enterprise_audit_manager
    ):
        """Test that track_agent_execution includes LangSmith tracing."""
        with patch(
            "universal_framework.observability.enterprise_audit.CrossPlatformTraceCorrelator"
        ) as mock_correlator_class:
            mock_correlator = MagicMock()
            mock_correlator.get_current_trace_context.return_value = {
                "session_hash": "hashed_session_123",
                "opentelemetry": {"trace_id": "test_trace_id"},
            }
            mock_correlator_class.return_value = mock_correlator
            enterprise_audit_manager.trace_correlator = mock_correlator

            with (
                patch.object(
                    enterprise_audit_manager, "_log_to_enterprise_system_with_langsmith"
                ) as mock_log_enterprise,
                patch.object(
                    enterprise_audit_manager, "_attribute_execution_cost"
                ) as mock_cost,
                patch.object(
                    enterprise_audit_manager, "_log_performance_to_langsmith"
                ) as mock_perf,
            ):

                execution_id = await enterprise_audit_manager.track_agent_execution(
                    "test_agent",
                    "session_123",
                    {"session_id": "session_123", "start_time": time.time()},
                    {"execution_time": 0.25},
                    success=True,
                )

                # Verify execution is tracked
                assert execution_id in enterprise_audit_manager.audit_registry
                record = enterprise_audit_manager.audit_registry[execution_id]

                # Verify LangSmith metadata is present
                assert "trace_metadata" in record
                assert "correlation_context" in record
                assert record["success"] is True

                # Verify all LangSmith integrations were called
                mock_log_enterprise.assert_called_once()
                mock_cost.assert_called_once()
                mock_perf.assert_called_once()

                # Verify privacy logger was called (existing functionality preserved)
                enterprise_audit_manager.privacy_logger.log_agent_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_compliance_event_with_cost_attribution(
        self, enterprise_audit_manager
    ):
        """Test that compliance events include cost attribution and LangSmith tracing."""
        with patch(
            "universal_framework.observability.enterprise_audit.CrossPlatformTraceCorrelator"
        ) as mock_correlator_class:
            mock_correlator = MagicMock()
            mock_correlator.get_current_trace_context.return_value = {
                "session_hash": "hashed_session_123",
                "correlation_timestamp": time.time(),
            }
            mock_correlator_class.return_value = mock_correlator
            enterprise_audit_manager.trace_correlator = mock_correlator

            with (
                patch.object(
                    enterprise_audit_manager, "_log_to_enterprise_system_with_langsmith"
                ) as mock_log_enterprise,
                patch.object(
                    enterprise_audit_manager, "_attribute_compliance_cost"
                ) as mock_cost,
                patch.object(
                    enterprise_audit_manager, "_log_performance_to_langsmith"
                ) as mock_perf,
            ):

                await enterprise_audit_manager.track_compliance_event(
                    "gdpr_data_processing",
                    "session_123",
                    {"data_type": "personal_info", "purpose": "user_request"},
                )

                # Verify compliance event is tracked
                assert len(enterprise_audit_manager.audit_events) == 1
                event = enterprise_audit_manager.audit_events[0]

                # Verify LangSmith metadata is present
                assert "trace_metadata" in event
                assert "correlation_context" in event
                assert event["event_type"] == "gdpr_data_processing"

                # Verify all LangSmith integrations were called
                mock_log_enterprise.assert_called_once()
                mock_cost.assert_called_once()
                mock_perf.assert_called_once()

    @pytest.mark.asyncio
    async def test_langsmith_circuit_breaker_fallback(
        self, enterprise_audit_manager, mock_langsmith_config
    ):
        """Test graceful fallback when LangSmith circuit breaker is open."""
        # Configure circuit breaker to raise exception
        mock_langsmith_config.circuit_breaker.__aenter__.side_effect = Exception(
            "LangSmith unavailable"
        )

        with patch.object(
            enterprise_audit_manager, "_log_with_fallback"
        ) as mock_fallback:

            record = {
                "event_type": "test_event",
                "timestamp": datetime.now().isoformat(),
                "session_id": "session_123",
            }

            await enterprise_audit_manager._log_to_enterprise_system_with_langsmith(
                "test", record
            )

            # Verify fallback was called
            mock_fallback.assert_called_once_with(
                "test", record, error="LangSmith unavailable"
            )

    @pytest.mark.asyncio
    async def test_cost_attribution_for_audit_operations(
        self, enterprise_audit_manager
    ):
        """Test that all audit operations are cost-attributed in LangSmith."""
        with patch.object(
            enterprise_audit_manager.cost_tracker, "create_cost_metadata"
        ) as mock_cost_metadata:
            mock_cost_metadata.return_value = {
                "agent_name": "audit_manager",
                "session_total_tokens": 10,
                "session_total_cost_usd": 0.001,
                "cost_efficiency_score": 10000.0,
            }

            await enterprise_audit_manager._attribute_audit_cost(
                "audit_123", "test_operation", "session_123", {"test": "metadata"}
            )

            # Verify cost tracker was called
            mock_cost_metadata.assert_called_once()

            # Verify cost attribution was logged
            # (This would be verified by checking the structlog calls in a real implementation)

    @pytest.mark.asyncio
    async def test_performance_metrics_with_langsmith_integration(
        self, enterprise_audit_manager
    ):
        """Test that performance metrics are logged to both compliance and LangSmith."""
        with patch(
            "universal_framework.observability.enterprise_audit.log_enterprise_performance_metrics"
        ) as mock_perf_log:

            record = {
                "execution_id": "exec_123",
                "agent_name": "test_agent",
                "trace_metadata": {"session_hash": "hashed_123"},
                "correlation_context": {"trace_id": "trace_123"},
            }

            await enterprise_audit_manager._log_performance_to_langsmith(
                "test_agent", "session_123", 15.0, record, True
            )

            # Verify performance was logged to LangSmith
            mock_perf_log.assert_called_once()
            args, kwargs = mock_perf_log.call_args
            assert args[1] == "test_agent"  # agent_name
            assert args[2] == "session_123"  # session_id
            assert args[3] == 15.0  # execution_time_ms

    @pytest.mark.asyncio
    async def test_health_check_with_langsmith_integration(
        self, enterprise_audit_manager, mock_langsmith_config
    ):
        """Test comprehensive health check including LangSmith status."""
        with patch(
            "universal_framework.observability.enterprise_audit.LoggingFactory"
        ) as mock_logging_factory:
            mock_logger = MagicMock()
            mock_logging_factory.create_compliance_logger.return_value = mock_logger

            health_status = (
                await enterprise_audit_manager.health_check_with_langsmith_integration()
            )

            # Verify comprehensive health status
            assert "langsmith_integration" in health_status
            assert "compliance_logging" in health_status
            assert "circuit_breaker_state" in health_status
            assert "trace_correlation" in health_status
            assert "cost_attribution" in health_status
            assert "overall_health" in health_status
            assert health_status["component"] == "enterprise_audit_manager"

            # Verify compliance logging was tested
            mock_logger.log_compliance_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_metrics_with_langsmith_status(
        self, enterprise_audit_manager, mock_langsmith_config
    ):
        """Test that performance metrics include LangSmith integration status."""
        metrics = (
            await enterprise_audit_manager.get_performance_metrics_with_langsmith()
        )

        # Verify comprehensive metrics structure
        assert "langsmith_integration" in metrics
        assert "performance_statistics" in metrics
        assert metrics["component"] == "enterprise_audit_manager"

        # Verify LangSmith-specific metrics
        langsmith_metrics = metrics["langsmith_integration"]
        assert "langsmith_enabled" in langsmith_metrics
        assert "circuit_breaker_available" in langsmith_metrics
        assert "trace_correlation_active" in langsmith_metrics
        assert "cost_tracking_enabled" in langsmith_metrics
        assert "circuit_breaker_state" in langsmith_metrics

    @pytest.mark.asyncio
    async def test_trace_correlation_in_all_operations(self, enterprise_audit_manager):
        """Test that all audit operations include trace correlation."""
        with patch(
            "universal_framework.observability.enterprise_audit.CrossPlatformTraceCorrelator"
        ) as mock_correlator_class:
            mock_correlator = MagicMock()
            correlation_context = {
                "session_hash": "hashed_session_123",
                "opentelemetry": {
                    "trace_id": "test_trace_id",
                    "span_id": "test_span_id",
                },
                "correlation_timestamp": time.time(),
            }
            mock_correlator.get_current_trace_context.return_value = correlation_context
            mock_correlator_class.return_value = mock_correlator
            enterprise_audit_manager.trace_correlator = mock_correlator

            with (
                patch.object(
                    enterprise_audit_manager, "_log_to_enterprise_system_with_langsmith"
                ),
                patch.object(enterprise_audit_manager, "_attribute_audit_cost"),
            ):

                # Test log_operation
                audit_id = await enterprise_audit_manager.log_operation(
                    "test_op", "session_123", {}
                )
                record = enterprise_audit_manager.audit_registry[audit_id]
                assert record["correlation_context"] == correlation_context

                # Test state update logging
                await enterprise_audit_manager.log_state_update(
                    "session_123", "test_agent", "update_event", ["field1"], "audit_456"
                )
                state_event = enterprise_audit_manager.audit_events[-1]
                assert state_event["correlation_context"] == correlation_context

                # Test security event logging
                await enterprise_audit_manager.log_security_event(
                    "session_123",
                    "security_violation",
                    "test_agent",
                    {"details": "test"},
                )
                security_event = enterprise_audit_manager.security_events[-1]
                assert security_event["correlation_context"] == correlation_context

    @pytest.mark.asyncio
    async def test_no_audit_logs_without_langsmith_tracing(
        self, enterprise_audit_manager
    ):
        """Test that all audit logs must include LangSmith tracing metadata."""
        with patch.object(
            enterprise_audit_manager, "_log_to_enterprise_system_with_langsmith"
        ) as mock_log_enterprise:

            # Test that log_operation always calls LangSmith integration
            await enterprise_audit_manager.log_operation(
                "test_operation", "session_123", {"test": "metadata"}
            )

            # Verify enterprise logging (which includes LangSmith) was called
            mock_log_enterprise.assert_called_once()

            # Verify the record includes required LangSmith metadata
            args, kwargs = mock_log_enterprise.call_args
            log_type, record = args
            assert "trace_metadata" in record
            assert "correlation_context" in record

    @pytest.mark.asyncio
    async def test_export_compliance_report_with_langsmith_tracing(
        self, enterprise_audit_manager
    ):
        """Test that compliance report export includes LangSmith tracing."""
        # Add some test data
        with (
            patch.object(
                enterprise_audit_manager, "_log_to_enterprise_system_with_langsmith"
            ),
            patch.object(enterprise_audit_manager, "_attribute_execution_cost"),
            patch.object(enterprise_audit_manager, "_log_performance_to_langsmith"),
        ):
            await enterprise_audit_manager.track_agent_execution(
                "test_agent",
                "session_123",
                {"session_id": "session_123", "start_time": time.time()},
                {"execution_time": 0.1},
            )

        with patch.object(
            enterprise_audit_manager, "get_audit_trail"
        ) as mock_get_trail:
            mock_get_trail.return_value = [
                {
                    "execution_id": "exec_123",
                    "agent_name": "test_agent",
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                    "trace_metadata": {"session_hash": "hashed_123"},
                }
            ]

            criteria = {"session_id": "session_123"}
            report = await enterprise_audit_manager.export_compliance_report(criteria)

            # Verify report includes LangSmith tracing information
            assert report["report_metadata"]["langsmith_traced"] is True
            assert "integrity_hash" in report


class TestEnterpriseAuditManagerValidation:
    """Test validation and error handling in EnterpriseAuditManager."""

    @pytest.mark.asyncio
    async def test_agent_execution_validation_with_langsmith_context(
        self, enterprise_audit_manager
    ):
        """Test that agent execution validation includes LangSmith context."""
        # Test empty agent name
        with pytest.raises(ComplianceError) as exc_info:
            await enterprise_audit_manager.track_agent_execution(
                "", "session_123", {}, {"execution_time": 0.1}
            )

        assert "Agent name is required" in str(exc_info.value)
        assert "SOC2_audit_trail" in str(exc_info.value)

        # Test invalid execution context
        with pytest.raises(ComplianceError) as exc_info:
            await enterprise_audit_manager.track_agent_execution(
                "test_agent", "session_123", "invalid_context", {"execution_time": 0.1}
            )

        assert "dictionary for audit compliance" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_query_parameter_validation_preserves_langsmith_integration(
        self, enterprise_audit_manager
    ):
        """Test that query validation preserves LangSmith integration capabilities."""
        # Test invalid session ID
        with pytest.raises(StateValidationError) as exc_info:
            await enterprise_audit_manager.get_audit_trail("")

        assert "session_id must be a non-empty string" in str(exc_info.value)

        # Test invalid time range
        start_time = datetime.now()
        end_time = start_time - timedelta(hours=1)

        with pytest.raises(StateValidationError) as exc_info:
            await enterprise_audit_manager.get_audit_trail(
                "session_123", start_time=start_time, end_time=end_time
            )

        assert "cannot be after end_time" in str(exc_info.value)


class TestLangSmithFallbackBehavior:
    """Test fallback behavior when LangSmith is unavailable."""

    @pytest.mark.asyncio
    async def test_fallback_logging_preserves_compliance(
        self, enterprise_audit_manager
    ):
        """Test that fallback logging still preserves compliance requirements."""
        with patch(
            "universal_framework.observability.enterprise_audit.LoggingFactory"
        ) as mock_logging_factory:
            mock_logger = MagicMock()
            mock_logging_factory.create_compliance_logger.return_value = mock_logger

            record = {
                "event_type": "test_event",
                "timestamp": datetime.now().isoformat(),
                "session_id": "session_123",
            }

            await enterprise_audit_manager._log_with_fallback(
                "test", record, error="LangSmith unavailable"
            )

            # Verify compliance logging was called twice:
            # 1. Original event
            # 2. Fallback warning
            assert mock_logger.log_compliance_event.call_count == 2

            # Verify fallback warning was logged
            fallback_call = mock_logger.log_compliance_event.call_args_list[1]
            assert fallback_call[1]["event_type"] == "audit_fallback_warning"

    @pytest.mark.asyncio
    async def test_circuit_breaker_triggers_on_langsmith_failure(
        self, enterprise_audit_manager, mock_langsmith_config
    ):
        """Test that circuit breaker is triggered when LangSmith fails."""
        # Configure circuit breaker to fail
        mock_langsmith_config.circuit_breaker.__aenter__.side_effect = Exception(
            "LangSmith error"
        )

        with patch.object(
            enterprise_audit_manager, "_log_with_fallback"
        ) as mock_fallback:

            record = {"event_type": "test", "session_id": "session_123"}
            await enterprise_audit_manager._log_to_enterprise_system_with_langsmith(
                "test", record
            )

            # Verify fallback was called with error
            mock_fallback.assert_called_once()
            call_args = mock_fallback.call_args
            assert "LangSmith error" in call_args[1]["error"]

            # Verify circuit breaker exit was called (error handling)
            mock_langsmith_config.circuit_breaker.__aexit__.assert_called_once()
