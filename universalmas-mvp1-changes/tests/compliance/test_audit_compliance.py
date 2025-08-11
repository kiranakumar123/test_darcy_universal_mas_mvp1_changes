import time
import tracemalloc
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from universal_framework.compliance import (
    EnterpriseAuditManager,
    PrivacySafeLogger,
)
from universal_framework.observability import EnterpriseLangSmithConfig


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
    config.circuit_breaker.__aenter__ = AsyncMock(return_value=config.circuit_breaker)
    config.circuit_breaker.__aexit__ = AsyncMock(return_value=None)
    config.enterprise_settings = {"max_trace_overhead_ms": 10.0}
    return config


@pytest.fixture
def audit_manager_with_langsmith(mock_langsmith_config):
    """Create an EnterpriseAuditManager with LangSmith integration for testing."""
    return EnterpriseAuditManager(
        PrivacySafeLogger(), mock_langsmith_config, hash_salt="test_salt"
    )


@pytest.mark.asyncio
async def test_agent_execution_tracking(audit_manager_with_langsmith):
    """Test agent execution tracking with LangSmith integration verification."""
    with (
        patch.object(
            audit_manager_with_langsmith, "_log_to_enterprise_system_with_langsmith"
        ) as mock_log_enterprise,
        patch.object(
            audit_manager_with_langsmith, "_attribute_execution_cost"
        ) as mock_cost,
        patch.object(
            audit_manager_with_langsmith, "_log_performance_to_langsmith"
        ) as mock_perf,
    ):

        context = {"session_id": "session_123", "user_input": "email jane@example.com"}
        exec_id = await audit_manager_with_langsmith.track_agent_execution(
            "requirements_collector",
            "session_123",
            context,
            {"execution_time": 0.25},
            success=True,
        )

        # Verify execution is tracked
        assert exec_id in audit_manager_with_langsmith.audit_registry
        assert audit_manager_with_langsmith.audit_registry[exec_id]["success"] is True

        # CRITICAL: Verify LangSmith event presence
        record = audit_manager_with_langsmith.audit_registry[exec_id]
        assert (
            "trace_metadata" in record
        ), "All audit events must include LangSmith trace metadata"
        assert (
            "correlation_context" in record
        ), "All audit events must include trace correlation"

        # Verify all LangSmith integrations were called
        mock_log_enterprise.assert_called_once(), "Audit must be logged to LangSmith"
        mock_cost.assert_called_once(), "Audit must include cost attribution"
        mock_perf.assert_called_once(), "Audit must include performance metrics"


@pytest.mark.asyncio
async def test_get_audit_trail_filtering(audit_manager_with_langsmith):
    """Test audit trail filtering with LangSmith tracing verification."""
    with (
        patch.object(
            audit_manager_with_langsmith, "_log_to_enterprise_system_with_langsmith"
        ),
        patch.object(audit_manager_with_langsmith, "_attribute_execution_cost"),
        patch.object(audit_manager_with_langsmith, "_log_performance_to_langsmith"),
    ):

        for i in range(10):
            await audit_manager_with_langsmith.track_agent_execution(
                f"test_agent_{i % 3}",
                "test_session_123",
                {"session_id": "test_session_123"},
                {"execution_time": 0.1 + (i * 0.05)},
                success=i % 2 == 0,
            )

        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=1)

        results = await audit_manager_with_langsmith.get_audit_trail(
            session_id="test_session_123",
            start_time=start_time,
            end_time=end_time,
            agent_names=["test_agent_0", "test_agent_1"],
            success_only=True,
        )

        assert results
        for r in results:
            assert r["agent_name"] in {"test_agent_0", "test_agent_1"}
            assert r["success"] is True
            ts = datetime.fromisoformat(r["timestamp"])
            assert start_time <= ts <= end_time

            # CRITICAL: Verify LangSmith event presence in all results
            assert (
                "trace_metadata" in r
            ), "All audit trail results must include LangSmith metadata"
            assert (
                "correlation_context" in r
            ), "All audit trail results must include trace correlation"


@pytest.mark.asyncio
async def test_export_compliance_report_formats(audit_manager_with_langsmith):
    """Test export compliance report formats with LangSmith tracing verification."""
    with (
        patch.object(
            audit_manager_with_langsmith, "_log_to_enterprise_system_with_langsmith"
        ),
        patch.object(audit_manager_with_langsmith, "_attribute_execution_cost"),
        patch.object(audit_manager_with_langsmith, "_log_performance_to_langsmith"),
    ):

        for _ in range(5):
            await audit_manager_with_langsmith.track_agent_execution(
                "export_agent",
                "export_session",
                {"session_id": "export_session"},
                {"execution_time": 0.1},
            )

        criteria = {
            "session_id": "export_session",
            "start_time": datetime.now() - timedelta(hours=1),
            "end_time": datetime.now() + timedelta(hours=1),
        }

        json_report = await audit_manager_with_langsmith.export_compliance_report(
            criteria, format="json"
        )
        assert json_report["report_metadata"]["format"] == "json"
        assert json_report["audit_data"]["audit_records"]

        # CRITICAL: Verify LangSmith tracing in report metadata
        assert (
            json_report["report_metadata"]["langsmith_traced"] is True
        ), "Export must be LangSmith traced"

        csv_report = await audit_manager_with_langsmith.export_compliance_report(
            criteria, format="csv"
        )
        assert csv_report["report_metadata"]["format"] == "csv"
        assert "timestamp,agent_name" in csv_report["audit_data"]
        assert (
            csv_report["report_metadata"]["langsmith_traced"] is True
        ), "CSV export must be LangSmith traced"

        xml_report = await audit_manager_with_langsmith.export_compliance_report(
            criteria, format="xml"
        )
        assert xml_report["report_metadata"]["format"] == "xml"
        assert "<ComplianceAuditReport>" in xml_report["audit_data"]
        assert (
            xml_report["report_metadata"]["langsmith_traced"] is True
        ), "XML export must be LangSmith traced"


@pytest.mark.asyncio
async def test_query_performance_under_100ms(audit_manager_with_langsmith):
    """Test query performance with LangSmith overhead monitoring."""
    with (
        patch.object(
            audit_manager_with_langsmith, "_log_to_enterprise_system_with_langsmith"
        ),
        patch.object(audit_manager_with_langsmith, "_attribute_execution_cost"),
        patch.object(audit_manager_with_langsmith, "_log_performance_to_langsmith"),
    ):

        for i in range(1000):
            await audit_manager_with_langsmith.track_agent_execution(
                f"perf_agent_{i % 5}",
                f"session_{i % 50}",
                {"session_id": f"session_{i % 50}"},
                {"execution_time": 0.1},
            )

        start = time.time()
        results = await audit_manager_with_langsmith.get_audit_trail(
            session_id="session_25",
        )
        duration = (time.time() - start) * 1000

        # Verify performance is under 100ms even with LangSmith overhead
        assert duration < 100, f"Query took {duration}ms, exceeding 100ms threshold"
        assert results

        # Verify all results have LangSmith metadata
        for result in results:
            assert (
                "trace_metadata" in result
            ), "Performance test results must include LangSmith metadata"


@pytest.mark.asyncio
async def test_export_generation_performance(audit_manager_with_langsmith):
    """Test export generation performance with LangSmith integration."""
    with (
        patch.object(
            audit_manager_with_langsmith, "_log_to_enterprise_system_with_langsmith"
        ),
        patch.object(audit_manager_with_langsmith, "_attribute_execution_cost"),
        patch.object(audit_manager_with_langsmith, "_log_performance_to_langsmith"),
    ):

        for i in range(500):
            await audit_manager_with_langsmith.track_agent_execution(
                f"export_agent_{i % 5}",
                "perf_export_session",
                {"session_id": "perf_export_session"},
                {"execution_time": 0.15},
            )

        start = time.time()
        report = await audit_manager_with_langsmith.export_compliance_report(
            {"session_id": "perf_export_session"},
            format="json",
        )
        duration = time.time() - start

        assert duration < 5, f"Export took {duration}s, exceeding 5s threshold"
        assert report["report_metadata"]["record_count"] == 500

        # CRITICAL: Verify LangSmith tracing in performance test
        assert (
            report["report_metadata"]["langsmith_traced"] is True
        ), "Performance export must be LangSmith traced"


@pytest.mark.asyncio
async def test_audit_trail_data_integrity(audit_manager_with_langsmith):
    """Test audit trail data integrity with LangSmith metadata preservation."""
    with (
        patch.object(
            audit_manager_with_langsmith, "_log_to_enterprise_system_with_langsmith"
        ),
        patch.object(audit_manager_with_langsmith, "_attribute_execution_cost"),
        patch.object(audit_manager_with_langsmith, "_log_performance_to_langsmith"),
    ):

        await audit_manager_with_langsmith.track_agent_execution(
            "integrity_agent",
            "integrity_session",
            {"session_id": "integrity_session"},
            {"execution_time": 0.2},
        )

        report = await audit_manager_with_langsmith.export_compliance_report(
            {"session_id": "integrity_session"},
            format="json",
        )
        integrity_hash = report["integrity_hash"]
        recomputed = audit_manager_with_langsmith._calculate_report_hash(
            report["audit_data"]
        )

        assert integrity_hash == recomputed, "Integrity hash must be consistent"

        # Verify LangSmith metadata doesn't break integrity
        assert report["report_metadata"]["langsmith_traced"] is True


@pytest.mark.asyncio
async def test_input_validation_time_range_edge_cases(audit_manager_with_langsmith):
    """Test input validation with time range edge cases."""
    start = datetime.now()
    end = start - timedelta(hours=1)

    with pytest.raises(Exception):  # Should raise StateValidationError
        await audit_manager_with_langsmith.get_audit_trail(
            session_id="test_session", start_time=start, end_time=end
        )


@pytest.mark.asyncio
async def test_invalid_parameter_error_messages(audit_manager_with_langsmith):
    """Test invalid parameter error messages."""
    with pytest.raises(Exception):  # Should raise StateValidationError
        await audit_manager_with_langsmith.get_audit_trail(session_id="")

    with pytest.raises(Exception):  # Should raise StateValidationError
        await audit_manager_with_langsmith.get_audit_trail(
            session_id="test", agent_names="not_a_list"
        )


@pytest.mark.asyncio
async def test_memory_efficiency_large_datasets(audit_manager_with_langsmith):
    """Test memory efficiency for large datasets with LangSmith overhead."""
    with (
        patch.object(
            audit_manager_with_langsmith, "_log_to_enterprise_system_with_langsmith"
        ),
        patch.object(audit_manager_with_langsmith, "_attribute_execution_cost"),
        patch.object(audit_manager_with_langsmith, "_log_performance_to_langsmith"),
    ):

        # Track memory usage
        tracemalloc.start()

        # Create large dataset
        for i in range(2000):
            await audit_manager_with_langsmith.track_agent_execution(
                f"memory_agent_{i % 10}",
                "memory_session",
                {"session_id": "memory_session"},
                {"execution_time": 0.1},
            )

        # Query large dataset
        results = await audit_manager_with_langsmith.get_audit_trail(
            session_id="memory_session"
        )

        # Check memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Verify results and memory efficiency
        assert len(results) == 2000
        assert peak < 50 * 1024 * 1024  # Less than 50MB peak memory

        # Verify all results have LangSmith metadata despite large size
        for result in results[:10]:  # Sample check
            assert "trace_metadata" in result
            assert "correlation_context" in result


@pytest.mark.asyncio
async def test_compliance_event_tracking_with_langsmith(audit_manager_with_langsmith):
    """Test compliance event tracking with mandatory LangSmith integration."""
    with patch(
        "universal_framework.observability.enterprise_audit.LoggingFactory"
    ) as mock_logging_factory:
        mock_logger = MagicMock()
        mock_logging_factory.create_compliance_logger.return_value = mock_logger

        with (
            patch.object(
                audit_manager_with_langsmith, "_log_to_enterprise_system_with_langsmith"
            ) as mock_log_enterprise,
            patch.object(
                audit_manager_with_langsmith, "_attribute_compliance_cost"
            ) as mock_cost,
            patch.object(
                audit_manager_with_langsmith, "_log_performance_to_langsmith"
            ) as mock_perf,
        ):

            await audit_manager_with_langsmith.track_compliance_event(
                "gdpr_data_access",
                "session_123",
                {"request_type": "data_export", "user_id": "user_456"},
            )

            # Verify compliance event was tracked
            assert len(audit_manager_with_langsmith.audit_events) == 1
            event = audit_manager_with_langsmith.audit_events[0]

            # CRITICAL: Verify LangSmith metadata is present
            assert (
                "trace_metadata" in event
            ), "Compliance events must include LangSmith metadata"
            assert (
                "correlation_context" in event
            ), "Compliance events must include trace correlation"
            assert event["event_type"] == "gdpr_data_access"

            # Verify all LangSmith integrations were called
            mock_log_enterprise.assert_called_once(), "Compliance events must be logged to LangSmith"
            mock_cost.assert_called_once(), "Compliance events must include cost attribution"
            mock_perf.assert_called_once(), "Compliance events must include performance tracking"


@pytest.mark.asyncio
async def test_health_check_langsmith_integration_required(
    audit_manager_with_langsmith,
):
    """Test that health check reports LangSmith integration status."""
    with patch(
        "universal_framework.observability.enterprise_audit.LoggingFactory"
    ) as mock_logging_factory:
        mock_logger = MagicMock()
        mock_logging_factory.create_compliance_logger.return_value = mock_logger

        health_status = (
            await audit_manager_with_langsmith.health_check_with_langsmith_integration()
        )

        # CRITICAL: Verify comprehensive health status includes LangSmith
        required_fields = [
            "langsmith_integration",
            "compliance_logging",
            "circuit_breaker_state",
            "trace_correlation",
            "cost_attribution",
            "overall_health",
        ]

        for field in required_fields:
            assert field in health_status, f"Health check must include {field} status"

        assert health_status["component"] == "enterprise_audit_manager"


@pytest.mark.asyncio
async def test_no_audit_without_langsmith_tracing(audit_manager_with_langsmith):
    """Test that NO audit operations occur without LangSmith tracing."""
    # This test ensures architectural compliance - no siloed audit logs

    with patch.object(
        audit_manager_with_langsmith, "_log_to_enterprise_system_with_langsmith"
    ) as mock_log_enterprise:
        # Mock to track that LangSmith integration is always called

        # Test log_operation
        await audit_manager_with_langsmith.log_operation(
            "test_operation", "session_123", {"test": "metadata"}
        )
        mock_log_enterprise.assert_called(), "log_operation must call LangSmith integration"

        # Reset mock
        mock_log_enterprise.reset_mock()

        # Test track_agent_execution
        with (
            patch.object(audit_manager_with_langsmith, "_attribute_execution_cost"),
            patch.object(audit_manager_with_langsmith, "_log_performance_to_langsmith"),
        ):
            await audit_manager_with_langsmith.track_agent_execution(
                "test_agent",
                "session_123",
                {"session_id": "session_123", "start_time": time.time()},
                {"execution_time": 0.1},
            )
            mock_log_enterprise.assert_called(), "track_agent_execution must call LangSmith integration"

        # Reset mock
        mock_log_enterprise.reset_mock()

        # Test track_compliance_event
        with (
            patch.object(audit_manager_with_langsmith, "_attribute_compliance_cost"),
            patch.object(audit_manager_with_langsmith, "_log_performance_to_langsmith"),
        ):
            await audit_manager_with_langsmith.track_compliance_event(
                "test_event", "session_123", {"test": "data"}
            )
            mock_log_enterprise.assert_called(), "track_compliance_event must call LangSmith integration"


@pytest.mark.asyncio
async def test_performance_metrics_include_langsmith_status(
    audit_manager_with_langsmith,
):
    """Test that performance metrics always include LangSmith integration status."""
    metrics = (
        await audit_manager_with_langsmith.get_performance_metrics_with_langsmith()
    )

    # CRITICAL: Verify LangSmith integration metrics are present
    assert (
        "langsmith_integration" in metrics
    ), "Performance metrics must include LangSmith status"

    langsmith_metrics = metrics["langsmith_integration"]
    required_langsmith_fields = [
        "langsmith_enabled",
        "circuit_breaker_available",
        "trace_correlation_active",
        "cost_tracking_enabled",
        "circuit_breaker_state",
    ]

    for field in required_langsmith_fields:
        assert field in langsmith_metrics, f"LangSmith metrics must include {field}"

    # Verify base performance metrics are preserved
    assert "performance_threshold_ms" in metrics
    assert "component" in metrics
    assert metrics["component"] == "enterprise_audit_manager"


# End of LangSmith-first EnterpriseAuditManager tests
# All audit, compliance, and performance operations now require LangSmith integration
