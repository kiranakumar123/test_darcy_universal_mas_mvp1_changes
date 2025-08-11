"""
Complete integration test for the new modular logging architecture.
Tests the entire dependency chain works correctly.
"""

import asyncio
import gc
import time
from unittest.mock import Mock

import pytest

from universal_framework.observability.agent_execution_logger import (
    AgentExecutionLogger,
)
from universal_framework.observability.langsmith_tracer import LangSmithTracer
from universal_framework.observability.modern_logger import (
    ModernUniversalFrameworkLogger,
)
from universal_framework.observability.structured_logger import StructuredLogger


class TestCompleteIntegration:
    """Test the complete modular logging system integration."""

    @pytest.mark.asyncio
    async def test_full_dependency_chain(self):
        """Test that the complete dependency chain works correctly."""

        # 1. Create the full stack using dependency injection
        tracer = LangSmithTracer("test-project", sampling_rate=1.0)
        structured_logger = StructuredLogger(tracers=[tracer])
        main_logger = ModernUniversalFrameworkLogger(
            component_name="integration_test", logger=structured_logger
        )

        # 2. Test agent-specific logging
        agent_logger = AgentExecutionLogger(main_logger)

        # 3. Execute full workflow
        async with main_logger.logging_session():
            # Test agent execution logging
            await agent_logger.log_agent_execution(
                agent_name="test_agent",
                session_id="test_session_123",
                execution_context={"duration_ms": 150},
                success=True,
            )

            # Test workflow transition logging
            await main_logger.log_workflow_transition(
                from_phase="discovery",
                to_phase="analysis",
                session_id="test_session_123",
                transition_context={"reason": "requirements_complete"},
            )

        # Verify no exceptions and proper execution
        assert True  # If we get here, the integration works

    def test_no_circular_imports(self):
        """Test that all imports resolve without circular dependencies."""
        try:
            # This should work without any import errors
            from universal_framework.observability import (
                LoggerProtocol,
                PrivacyFilterProtocol,
                TracerProtocol,
                UniversalFrameworkLogger,
            )

            # Test that we can create instances
            logger = UniversalFrameworkLogger("test_component")
            assert logger is not None
            assert logger.component_name == "test_component"

        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    @pytest.mark.asyncio
    async def test_performance_requirements(self):
        """Test that the modular architecture meets <5ms logging requirement."""

        logger = ModernUniversalFrameworkLogger("performance_test")

        # Measure logging performance
        start_time = time.perf_counter()

        await logger.log_agent_execution(
            agent_name="perf_test_agent",
            session_id="perf_session",
            execution_context={"test": "data"},
            success=True,
        )

        end_time = time.perf_counter()
        logging_duration_ms = (end_time - start_time) * 1000

        # Should be well under 5ms requirement
        assert (
            logging_duration_ms < 5.0
        ), f"Logging took {logging_duration_ms}ms, exceeds 5ms requirement"

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self):
        """Test that the logging system doesn't create memory leaks."""

        # Measure initial memory
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Create and destroy 50 logger instances
        for i in range(50):
            logger = ModernUniversalFrameworkLogger(f"test_component_{i}")
            await logger.log_agent_execution(
                agent_name="test_agent",
                session_id=f"session_{i}",
                execution_context={"iteration": i},
                success=True,
            )
            del logger

        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())

        # Should not have significant object growth
        object_growth = final_objects - initial_objects
        assert (
            object_growth < 50
        ), f"Memory leak detected: {object_growth} objects created"

    @pytest.mark.asyncio
    async def test_concurrent_logging_safety(self):
        """Test that concurrent logging operations are thread-safe."""

        logger = ModernUniversalFrameworkLogger("concurrent_test")

        # Create 25 concurrent logging operations
        async def log_operation(session_num):
            await logger.log_agent_execution(
                agent_name=f"agent_{session_num}",
                session_id=f"session_{session_num}",
                execution_context={"concurrent_test": True},
                success=True,
            )

        # Run all operations concurrently
        tasks = [log_operation(i) for i in range(25)]
        await asyncio.gather(*tasks)

        # Should complete without errors
        assert True

    def test_protocol_compliance(self):
        """Test that all implementations comply with protocols."""

        # Test LangSmith tracer implements TracerProtocol
        tracer = LangSmithTracer("test-project")
        assert hasattr(tracer, "correlate_event")
        assert hasattr(tracer, "is_enabled")
        assert callable(tracer.correlate_event)
        assert callable(tracer.is_enabled)

        # Test StructuredLogger implements LoggerProtocol
        structured_logger = StructuredLogger(tracers=[tracer])
        assert hasattr(structured_logger, "emit")
        assert hasattr(structured_logger, "flush")
        assert callable(structured_logger.emit)
        assert callable(structured_logger.flush)

    def test_dependency_injection_flexibility(self):
        """Test that all dependencies can be injected."""
        from universal_framework.observability.protocols import (
            LoggerProtocol,
            TracerProtocol,
        )

        # Mock all dependencies
        mock_logger = Mock(spec=LoggerProtocol)
        mock_tracer = Mock(spec=TracerProtocol)

        # Should accept mocked dependencies
        logger = ModernUniversalFrameworkLogger(
            component_name="test_component", logger=mock_logger, tracers=[mock_tracer]
        )

        assert logger._logger == mock_logger
        assert mock_tracer in logger._tracers
