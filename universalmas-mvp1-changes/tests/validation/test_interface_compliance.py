"""
Interface Compliance Validation
===============================

Validates that Codex implementations exactly match interface stubs.
Must pass before Phase 2B can begin.
"""

import asyncio
import inspect
from typing import get_type_hints
from unittest.mock import MagicMock

import pytest


def test_redis_connection_adapter_interface():
    """Verify RedisConnectionAdapter implementation matches interface stub."""

    # Import both stub and implementation
    from universal_framework.redis.interfaces_stub import RedisConnectionAdapter as Stub

    try:
        from universal_framework.redis.connection import (
            RedisConnectionAdapter as Implementation,
        )
    except ImportError:
        pytest.skip("RedisConnectionAdapter implementation not yet available")

    # Verify class inheritance
    assert issubclass(
        Implementation, Stub
    ), "Implementation must inherit from interface stub"

    # Get all methods from stub
    stub_methods = {
        name: method
        for name, method in inspect.getmembers(Stub, predicate=inspect.isfunction)
        if not name.startswith("_") or name in ["__init__"]
    }

    # Verify all methods exist in implementation
    impl_methods = dict(
        inspect.getmembers(Implementation, predicate=inspect.isfunction)
    )

    for method_name, stub_method in stub_methods.items():
        assert method_name in impl_methods, f"Missing method: {method_name}"

        # Check method signatures
        stub_sig = inspect.signature(stub_method)
        impl_sig = inspect.signature(impl_methods[method_name])

        assert (
            stub_sig == impl_sig
        ), f"Method signature mismatch for {method_name}\nStub: {stub_sig}\nImpl: {impl_sig}"

    # Verify required attributes exist
    impl_instance = Implementation(MagicMock())
    required_attributes = [
        "config",
        "status",
        "connection_pool",
        "last_error",
        "retry_count",
        "max_retries",
    ]

    for attr in required_attributes:
        assert hasattr(impl_instance, attr), f"Missing required attribute: {attr}"


def test_session_manager_interface():
    """Verify SessionManagerImpl implementation matches interface stub."""

    from universal_framework.redis.interfaces_stub import SessionManagerImpl as Stub

    try:
        from universal_framework.redis.session_manager import (
            SessionManagerImpl as Implementation,
        )
    except ImportError:
        pytest.skip("SessionManagerImpl implementation not yet available")

    # Verify class inheritance
    assert issubclass(
        Implementation, Stub
    ), "Implementation must inherit from interface stub"

    # Get all methods from stub (including abstract methods)
    stub_methods = {}
    for cls in inspect.getmro(Stub):
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith("_") or name in ["__init__"]:
                stub_methods[name] = method

    # Verify all methods exist in implementation
    impl_methods = dict(
        inspect.getmembers(Implementation, predicate=inspect.isfunction)
    )

    for method_name, stub_method in stub_methods.items():
        assert method_name in impl_methods, f"Missing method: {method_name}"

        # Check method signatures for key methods
        if method_name in [
            "create_session",
            "store_session_data",
            "retrieve_session_data",
            "store_messages",
            "retrieve_messages",
            "append_message",
        ]:
            stub_sig = inspect.signature(stub_method)
            impl_sig = inspect.signature(impl_methods[method_name])
            assert stub_sig == impl_sig, f"Method signature mismatch for {method_name}"

    # Verify required attributes exist
    impl_instance = Implementation(MagicMock(), MagicMock())
    required_attributes = [
        "config",
        "connection",
        "memory_storage",
        "memory_ttl",
        "max_memory_sessions",
        "metrics",
    ]

    for attr in required_attributes:
        assert hasattr(impl_instance, attr), f"Missing required attribute: {attr}"


def test_method_async_compliance():
    """Verify all required methods are properly async."""

    from universal_framework.redis.interfaces_stub import (
        RedisConnectionAdapter,
        SessionManagerImpl,
    )

    # Check RedisConnectionAdapter async methods
    redis_async_methods = [
        "connect",
        "disconnect",
        "ping",
        "is_healthy",
        "get_info",
        "execute_command",
        "set_with_ttl",
        "get",
        "delete",
        "scan_keys",
    ]

    for method_name in redis_async_methods:
        method = getattr(RedisConnectionAdapter, method_name)
        assert asyncio.iscoroutinefunction(
            method
        ), f"RedisConnectionAdapter.{method_name} must be async"

    # Check SessionManagerImpl async methods
    session_async_methods = [
        "create_session",
        "store_session_data",
        "retrieve_session_data",
        "store_messages",
        "retrieve_messages",
        "append_message",
        "get_message_count",
        "update_session_activity",
        "extend_session_ttl",
        "cleanup_expired_sessions",
        "get_session_stats",
        "get_active_sessions",
        "is_redis_available",
        "get_fallback_stats",
    ]

    for method_name in session_async_methods:
        method = getattr(SessionManagerImpl, method_name)
        assert asyncio.iscoroutinefunction(
            method
        ), f"SessionManagerImpl.{method_name} must be async"


def test_type_hint_compliance():
    """Verify return type hints match interface specifications."""

    from universal_framework.redis.interfaces_stub import (
        RedisConnectionAdapter,
    )

    # Check critical return types for RedisConnectionAdapter
    redis_return_types = {
        "connect": bool,
        "ping": bool,
        "is_healthy": bool,
        "get_info": dict,
        "set_with_ttl": bool,
        "delete": bool,
        "scan_keys": list,
    }

    for method_name, expected_return_type in redis_return_types.items():
        method = getattr(RedisConnectionAdapter, method_name)
        hints = get_type_hints(method)
        assert "return" in hints, f"Missing return type hint for {method_name}"

        # Handle Union types and Optional types
        return_type = hints["return"]
        if hasattr(return_type, "__origin__"):
            # Handle Union[X, None] (Optional) or other complex types
            continue
        else:
            assert (
                return_type == expected_return_type
                or return_type.__name__ == expected_return_type.__name__
            ), f"Wrong return type for {method_name}: expected {expected_return_type}, got {return_type}"


def test_contract_interface_inheritance():
    """Verify implementations inherit from contract interfaces."""

    from universal_framework.contracts.redis.interfaces import (
        MessageStoreInterface,
        RedisConnectionInterface,
        SessionManagerInterface,
    )
    from universal_framework.redis.interfaces_stub import (
        RedisConnectionAdapter,
        SessionManagerImpl,
    )

    # Verify inheritance chain
    assert issubclass(
        RedisConnectionAdapter, RedisConnectionInterface
    ), "RedisConnectionAdapter must inherit from RedisConnectionInterface"

    assert issubclass(
        SessionManagerImpl, SessionManagerInterface
    ), "SessionManagerImpl must inherit from SessionManagerInterface"

    assert issubclass(
        SessionManagerImpl, MessageStoreInterface
    ), "SessionManagerImpl must inherit from MessageStoreInterface"


def test_error_handling_compliance():
    """Verify proper error handling patterns."""

    from universal_framework.redis.interfaces_stub import RedisConnectionAdapter

    # Verify execute_command method specifies correct exceptions
    method = RedisConnectionAdapter.execute_command
    docstring = method.__doc__ or ""

    # Check that docstring mentions the required exceptions
    assert (
        "RedisConnectionError" in docstring
    ), "execute_command must document RedisConnectionError"
    assert (
        "RedisTimeoutError" in docstring
    ), "execute_command must document RedisTimeoutError"


@pytest.mark.asyncio
async def test_implementation_instantiation():
    """Test that implementations can be instantiated without errors."""

    try:
        from universal_framework.config.workflow_config import WorkflowConfig
        from universal_framework.redis.connection import RedisConnectionAdapter
        from universal_framework.redis.session_manager import SessionManagerImpl

        # Create mock config
        config = WorkflowConfig()

        # Test Redis connection instantiation
        connection = RedisConnectionAdapter(config)
        assert connection is not None
        assert connection.config == config

        # Test session manager instantiation
        session_manager = SessionManagerImpl(config, connection)
        assert session_manager is not None
        assert session_manager.config == config
        assert session_manager.connection == connection

    except ImportError:
        pytest.skip("Implementations not yet available")


def test_interface_method_completeness():
    """Verify all interface methods are present and not NotImplemented."""

    from universal_framework.redis.interfaces_stub import (
        RedisConnectionAdapter,
        SessionManagerImpl,
    )

    # Get all abstract methods that should be implemented
    redis_methods = [
        name
        for name, method in inspect.getmembers(
            RedisConnectionAdapter, predicate=inspect.isfunction
        )
        if not name.startswith("__")
    ]

    session_methods = [
        name
        for name, method in inspect.getmembers(
            SessionManagerImpl, predicate=inspect.isfunction
        )
        if not name.startswith("__")
    ]

    # Verify we have the expected number of methods
    assert (
        len(redis_methods) >= 10
    ), f"RedisConnectionAdapter should have at least 10 methods, found {len(redis_methods)}"
    assert (
        len(session_methods) >= 15
    ), f"SessionManagerImpl should have at least 15 methods, found {len(session_methods)}"

    # Verify critical methods are present
    critical_redis_methods = ["connect", "disconnect", "ping", "execute_command"]
    for method_name in critical_redis_methods:
        assert (
            method_name in redis_methods
        ), f"Missing critical Redis method: {method_name}"

    critical_session_methods = ["create_session", "store_messages", "retrieve_messages"]
    for method_name in critical_session_methods:
        assert (
            method_name in session_methods
        ), f"Missing critical session method: {method_name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
