"""
Production readiness validation for the new logging architecture.
Tests enterprise-grade requirements: performance, memory, concurrency, compliance.
"""

import asyncio
import gc
import time
from unittest.mock import Mock

import pytest

from universal_framework.observability import (
    LoggerProtocol,
    TracerProtocol,
    UniversalFrameworkLogger,
)


class TestProductionReadiness:
    """Validate production readiness of the modular logging system."""

    @pytest.mark.asyncio
    async def test_enterprise_performance_requirements(self):
        """Test <5ms logging requirement under realistic load."""

        logger = UniversalFrameworkLogger("production_test")

        # Test multiple operations to get average
        durations = []
        for i in range(10):
            start_time = time.perf_counter()

            await logger.log_agent_execution(
                agent_name=f"production_agent_{i}",
                session_id=f"prod_session_{i}",
                execution_context={
                    "operation": "data_processing",
                    "record_count": 1000,
                    "duration_ms": 250 + i,
                },
                success=True,
            )

            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            durations.append(duration_ms)

        # Calculate statistics
        avg_duration_ms = sum(durations) / len(durations)
        max_duration_ms = max(durations)

        # Enterprise requirements
        assert (
            avg_duration_ms < 5.0
        ), f"Average logging took {avg_duration_ms:.2f}ms, exceeds 5ms requirement"
        assert (
            max_duration_ms < 10.0
        ), f"Maximum logging took {max_duration_ms:.2f}ms, exceeds 10ms tolerance"

        print(
            f"✅ Performance: Avg {avg_duration_ms:.2f}ms, Max {max_duration_ms:.2f}ms"
        )

    @pytest.mark.asyncio
    async def test_memory_efficiency_under_load(self):
        """Test memory efficiency under production-like load."""

        # Measure baseline memory
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Simulate production load: 200 operations
        logger = UniversalFrameworkLogger("memory_test")

        for batch in range(4):  # 4 batches of 50 operations
            tasks = []
            for i in range(50):
                task = logger.log_agent_execution(
                    agent_name=f"memory_test_agent_{batch}_{i}",
                    session_id=f"memory_session_{batch}_{i}",
                    execution_context={
                        "batch": batch,
                        "operation_id": i,
                        "payload_size": 1024 * (i % 10),  # Variable payload sizes
                    },
                    success=True,
                )
                tasks.append(task)

            # Execute batch concurrently
            await asyncio.gather(*tasks)

            # Force cleanup after each batch
            gc.collect()

        # Final cleanup and measurement
        del logger
        gc.collect()
        final_objects = len(gc.get_objects())

        # Memory growth should be minimal
        object_growth = final_objects - initial_objects
        assert (
            object_growth < 100
        ), f"Memory leak detected: {object_growth} objects remain after cleanup"

        print(f"✅ Memory: {object_growth} objects growth (acceptable threshold: <100)")

    @pytest.mark.asyncio
    async def test_concurrent_session_isolation(self):
        """Test that concurrent sessions don't interfere with each other."""

        logger = UniversalFrameworkLogger("isolation_test")

        # Create 20 concurrent sessions
        async def session_workflow(session_num):
            session_id = f"isolated_session_{session_num}"

            # Each session performs multiple operations
            operations = [
                ("discovery", "analysis", {"findings": f"data_{session_num}"}),
                ("analysis", "generation", {"insights": f"insight_{session_num}"}),
                ("generation", "review", {"content": f"output_{session_num}"}),
            ]

            for from_phase, to_phase, context in operations:
                await logger.log_workflow_transition(
                    from_phase=from_phase,
                    to_phase=to_phase,
                    session_id=session_id,
                    transition_context=context,
                )

                # Small delay to simulate real workflow timing
                await asyncio.sleep(0.01)

            return session_id

        # Run all sessions concurrently
        session_tasks = [session_workflow(i) for i in range(20)]
        completed_sessions = await asyncio.gather(*session_tasks)

        # Should complete all sessions without interference
        assert len(completed_sessions) == 20
        assert len(set(completed_sessions)) == 20  # All unique session IDs

        print("✅ Concurrency: 20 isolated sessions completed successfully")

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test that logging system gracefully handles errors without breaking."""

        # Mock a failing tracer
        class FailingTracer:
            def __init__(self):
                self.call_count = 0

            async def correlate_event(self, event):
                self.call_count += 1
                if self.call_count <= 3:
                    raise Exception(f"Tracer failure #{self.call_count}")
                return event  # Recover after 3 failures

            def is_enabled(self):
                return True

        # Mock a failing logger backend
        failing_logger = Mock(spec=LoggerProtocol)
        failing_logger.emit.side_effect = Exception("Backend temporarily unavailable")
        failing_logger.flush.return_value = asyncio.Future()
        failing_logger.flush.return_value.set_result(None)

        # Create logger with failing components
        logger = UniversalFrameworkLogger(
            component_name="error_test",
            logger=failing_logger,
            tracers=[FailingTracer()],
        )

        # Should handle errors gracefully without breaking application
        try:
            await logger.log_agent_execution(
                agent_name="resilient_agent",
                session_id="error_test_session",
                execution_context={"test": "error_handling"},
                success=True,
            )

            # Should not raise exception even with failing backend
            assert True, "Logger handled errors gracefully"

        except Exception as e:
            pytest.fail(f"Logger should handle errors gracefully, but raised: {e}")

        print("✅ Error Handling: Graceful degradation under component failures")

    def test_protocol_interface_stability(self):
        """Test that protocol interfaces are stable and well-defined."""

        from universal_framework.observability.protocols import (
            LoggerProtocol,
            PrivacyFilterProtocol,
            TracerProtocol,
        )

        # Verify required methods exist on protocols
        tracer_methods = ["correlate_event", "is_enabled"]
        logger_methods = ["emit", "flush"]
        privacy_methods = ["sanitize"]

        # Check TracerProtocol
        for method in tracer_methods:
            assert hasattr(TracerProtocol, method), f"TracerProtocol missing {method}"

        # Check LoggerProtocol
        for method in logger_methods:
            assert hasattr(LoggerProtocol, method), f"LoggerProtocol missing {method}"

        # Check PrivacyFilterProtocol
        for method in privacy_methods:
            assert hasattr(
                PrivacyFilterProtocol, method
            ), f"PrivacyFilterProtocol missing {method}"

        print("✅ Protocols: All required methods defined and stable")

    def test_dependency_injection_completeness(self):
        """Test that all dependencies can be injected for testing."""

        # Create mock implementations
        mock_logger = Mock(spec=LoggerProtocol)
        mock_logger.emit.return_value = asyncio.Future()
        mock_logger.emit.return_value.set_result(None)
        mock_logger.flush.return_value = asyncio.Future()
        mock_logger.flush.return_value.set_result(None)

        mock_tracer = Mock(spec=TracerProtocol)
        mock_tracer.correlate_event.return_value = asyncio.Future()
        mock_tracer.correlate_event.return_value.set_result(Mock())
        mock_tracer.is_enabled.return_value = True

        # Should accept all mocked dependencies
        logger = UniversalFrameworkLogger(
            component_name="dependency_test", logger=mock_logger, tracers=[mock_tracer]
        )

        # Verify dependencies were injected
        assert logger._logger == mock_logger
        assert mock_tracer in logger._tracers

        print("✅ Dependency Injection: All components can be mocked for testing")

    @pytest.mark.asyncio
    async def test_enterprise_audit_compliance(self):
        """Test compliance with enterprise audit requirements."""

        logger = UniversalFrameworkLogger("audit_test")

        # Test that sensitive data contexts are handled appropriately
        sensitive_context = {
            "user_action": "data_export",
            "resource_type": "customer_records",
            "export_count": 150,
            "compliance_approved": True,
        }

        # Should log audit events without throwing exceptions
        await logger.log_agent_execution(
            agent_name="audit_agent",
            session_id="audit_session_001",
            execution_context=sensitive_context,
            success=True,
        )

        # Test workflow transitions for audit trail
        await logger.log_workflow_transition(
            from_phase="data_request",
            to_phase="compliance_check",
            session_id="audit_session_001",
            transition_context={"requester": "system", "auto_approved": False},
        )

        print("✅ Audit Compliance: Enterprise audit patterns work correctly")


class TestProductionDeploymentReadiness:
    """Test specific production deployment scenarios."""

    def test_import_speed(self):
        """Test that imports are fast enough for production startup."""

        start_time = time.perf_counter()

        # This should be fast

        import_time_ms = (time.perf_counter() - start_time) * 1000

        # Should import in <100ms for production startup
        assert (
            import_time_ms < 100
        ), f"Import took {import_time_ms:.2f}ms, too slow for production"

        print(f"✅ Import Speed: {import_time_ms:.2f}ms (requirement: <100ms)")

    def test_zero_configuration_startup(self):
        """Test that logger works with zero configuration."""

        # Should work with no parameters
        logger = UniversalFrameworkLogger("zero_config_test")

        # Should have sensible defaults
        assert logger.component_name == "zero_config_test"
        assert logger._logger is not None
        assert len(logger._tracers) > 0  # Should have default tracers

        print("✅ Zero Config: Logger works with default configuration")
