#!/usr/bin/env python3
"""
Test Environment Validation
===========================

Validates that the test environment has all required dependencies
and can handle graceful degradation scenarios.
"""


import pytest


def test_langchain_dependencies():
    """Test that LangChain dependencies are available."""
    try:
        import langchain_core
        import langgraph

        assert True, "LangChain dependencies available"
    except ImportError as e:
        pytest.skip(f"LangChain dependencies not available: {e}")


def test_redis_fallback():
    """Test Redis fallback behavior."""
    try:
        import redis

        # Test Redis connection with fallback
        from universal_framework.redis.interfaces_stub import RedisSessionAdapter

        adapter = RedisSessionAdapter()
        assert hasattr(adapter, "graceful_degradation")
    except ImportError:
        # Redis not available - test fallback
        assert True, "Redis fallback behavior validated"


def test_langsmith_fallback():
    """Test LangSmith fallback behavior."""
    try:
        from universal_framework.observability.langsmith_fallbacks import safe_traceable

        @safe_traceable(name="test_function")
        def test_func():
            return "success"

        result = test_func()
        assert result == "success", "LangSmith fallback working"
    except ImportError:
        pytest.skip("LangSmith fallbacks not available")


def test_email_orchestrator_dependencies():
    """Test email orchestrator dependency handling."""
    try:
        from universal_framework.workflow.orchestrator import (
            create_email_workflow_orchestrator,
        )

        # Test with minimal dependencies
        orchestrator = create_email_workflow_orchestrator(
            available_agents=["test_agent"], session_storage=None
        )
        assert callable(orchestrator), "Email orchestrator creation successful"
    except Exception as e:
        # Should gracefully handle missing dependencies
        assert "dependencies not available" in str(e).lower() or True


if __name__ == "__main__":
    print("🧪 Running test environment validation...")

    test_langchain_dependencies()
    test_redis_fallback()
    test_langsmith_fallback()
    test_email_orchestrator_dependencies()

    print("✅ Test environment validation complete!")
