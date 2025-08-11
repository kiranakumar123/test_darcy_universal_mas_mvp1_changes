# ruff: noqa
# fmt: off
"""
Configuration Completeness Validation
=====================================

Validates that WorkflowConfig includes all required fields for Universal Framework.
Must pass before Phase 2A can begin.
"""

import os
from dataclasses import fields

import pytest


def test_workflow_config_exists():
    """Verify WorkflowConfig class exists and can be imported."""

    try:
        from universal_framework.config.workflow_config import WorkflowConfig
    except ImportError as e:
        pytest.fail(f"Cannot import WorkflowConfig: {e}")

    # Verify it's a dataclass
    assert hasattr(
        WorkflowConfig, "__dataclass_fields__"
    ), "WorkflowConfig must be a dataclass"


def test_redis_configuration_fields():
    """Verify all Redis configuration fields are present."""

    from universal_framework.config.workflow_config import WorkflowConfig

    required_redis_fields = {
        "enable_redis_optimization": bool,
        "redis_host": str,
        "redis_port": str,  # String for safe parsing
        "redis_db": str,  # String for safe parsing
        "redis_password": (str, type(None)),  # Optional[str]
        "redis_ttl_hours": str,  # String for safe parsing
        "redis_url": (str, type(None)),  # Optional[str] - NEW requirement
    }

    config_fields = {field.name: field.type for field in fields(WorkflowConfig)}

    for field_name, expected_type in required_redis_fields.items():
        assert (
            field_name in config_fields
        ), f"Missing Redis configuration field: {field_name}"

        # Handle Optional types and Union types
        actual_type = config_fields[field_name]
        if isinstance(expected_type, tuple):
            # For Optional types, check if actual type includes the expected types
            continue  # Skip complex type checking for now
        else:
            assert (
                actual_type == expected_type or str(actual_type) == str(expected_type)
            ), f"Wrong type for {field_name}: expected {expected_type}, got {actual_type}"


def test_core_framework_fields():
    """Verify core Universal Framework configuration fields."""

    from universal_framework.config.workflow_config import WorkflowConfig

    required_framework_fields = {
        "enable_debug": bool,
        "enable_parallel_processing": bool,
        "log_level": str,
        "enable_metrics": bool,  # NEW requirement
    }

    config_fields = {field.name: field.type for field in fields(WorkflowConfig)}

    for field_name, expected_type in required_framework_fields.items():
        assert (
            field_name in config_fields
        ), f"Missing framework configuration field: {field_name}"


def test_security_configuration_fields():
    """Verify security configuration fields."""

    from universal_framework.config.workflow_config import WorkflowConfig

    required_security_fields = {
        "jwt_secret_key": (str, type(None)),  # Optional[str]
        "session_timeout_hours": str,  # String for safe parsing
        "enable_auth_validation": bool,  # NEW requirement
    }

    config_fields = {field.name: field.type for field in fields(WorkflowConfig)}

    for field_name, expected_type in required_security_fields.items():
        assert (
            field_name in config_fields
        ), f"Missing security configuration field: {field_name}"


def test_performance_configuration_fields():
    """Verify performance configuration fields."""

    from universal_framework.config.workflow_config import WorkflowConfig

    required_performance_fields = {
        "max_execution_time_seconds": str,  # String for safe parsing
        "agent_timeout_seconds": str,  # String for safe parsing
        "max_concurrent_sessions": str,  # String for safe parsing
        "session_cache_size": str,  # String for safe parsing
    }

    config_fields = {field.name: field.type for field in fields(WorkflowConfig)}

    for field_name, expected_type in required_performance_fields.items():
        assert (
            field_name in config_fields
        ), f"Missing performance configuration field: {field_name}"


def test_session_management_fields():
    """Verify session management configuration fields."""

    from universal_framework.config.workflow_config import WorkflowConfig

    required_session_fields = {
        "session_cleanup_interval": str,  # String for safe parsing
        "max_session_age_hours": str,  # String for safe parsing
    }

    config_fields = {field.name: field.type for field in fields(WorkflowConfig)}

    for field_name, expected_type in required_session_fields.items():
        assert (
            field_name in config_fields
        ), f"Missing session management field: {field_name}"


def test_environment_variable_loading():
    """Verify environment variables are loaded with proper defaults."""

    from universal_framework.config.workflow_config import WorkflowConfig

    # Test default values
    config = WorkflowConfig()

    # Check Redis defaults
    assert (
        config.enable_redis_optimization == False
    ), "Redis should be disabled by default"
    assert config.redis_host == "localhost", "Default Redis host should be localhost"
    assert config.redis_port == "6379", "Default Redis port should be 6379"
    assert config.redis_db == "0", "Default Redis DB should be 0"
    assert config.redis_ttl_hours == "24", "Default TTL should be 24 hours"

    # Check framework defaults
    assert config.enable_debug == False, "Debug should be disabled by default"
    assert (
        config.enable_parallel_processing == False
    ), "Parallel processing should be disabled by default"
    assert config.log_level == "INFO", "Default log level should be INFO"

    # Check performance defaults
    assert (
        config.max_execution_time_seconds == "30"
    ), "Default execution time should be 30 seconds"
    assert (
        config.agent_timeout_seconds == "5"
    ), "Default agent timeout should be 5 seconds"


def test_environment_variable_override():
    """Test that environment variables override defaults."""

    from universal_framework.config.workflow_config import WorkflowConfig

    # Set test environment variables
    test_env = {
        "ENABLE_REDIS_OPTIMIZATION": "true",
        "REDIS_HOST": "test-redis",
        "REDIS_PORT": "6380",
        "ENABLE_DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "SESSION_TIMEOUT_HOURS": "12",
    }

    # Backup original values
    original_env = {}
    for key in test_env:
        original_env[key] = os.environ.get(key)
        os.environ[key] = test_env[key]

    try:
        # Create config with environment overrides
        config = WorkflowConfig()

        # Verify overrides took effect
        assert config.enable_redis_optimization == True
        assert config.redis_host == "test-redis"
        assert config.redis_port == "6380"
        assert config.enable_debug == True
        assert config.log_level == "DEBUG"
        assert config.session_timeout_hours == "12"

    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_validation_method_exists():
    """Verify validate() method exists and returns list of errors."""

    from universal_framework.config.workflow_config import WorkflowConfig

    config = WorkflowConfig()

    # Verify validate method exists
    assert hasattr(config, "validate"), "WorkflowConfig must have validate() method"
    assert callable(config.validate), "validate must be callable"

    # Test validation with valid config
    errors = config.validate()
    assert isinstance(errors, list), "validate() must return a list"

    # Test validation with invalid config
    invalid_config = WorkflowConfig(
        enable_redis_optimization=True,
        redis_host="",  # Invalid: empty host
        redis_port="0",  # Invalid: port 0
    )

    errors = invalid_config.validate()
    assert isinstance(errors, list), "validate() must return a list"
    assert len(errors) > 0, "validate() should return errors for invalid config"
    assert any(
        "redis_host" in error for error in errors
    ), "Should have redis_host error"
    assert any(
        "redis_port" in error for error in errors
    ), "Should have redis_port error"


def test_sanitized_redis_url_method():
    """Verify get_sanitized_redis_url() method exists and works correctly."""

    from universal_framework.config.workflow_config import WorkflowConfig

    config = WorkflowConfig()

    # Verify method exists
    assert hasattr(
        config, "get_sanitized_redis_url"
    ), "WorkflowConfig must have get_sanitized_redis_url() method"
    assert callable(
        config.get_sanitized_redis_url
    ), "get_sanitized_redis_url must be callable"

    # Test without password
    config_no_password = WorkflowConfig(
        redis_host="localhost", redis_port="6379", redis_db="0"
    )
    sanitized_url = config_no_password.get_sanitized_redis_url()
    assert (
        sanitized_url == "redis://localhost:6379/0"
    ), f"Expected 'redis://localhost:6379/0', got '{sanitized_url}'"

    # Test with password
    config_with_password = WorkflowConfig(
        redis_host="localhost",
        redis_port="6379",
        redis_db="0",
        redis_password="secret123",
    )
    sanitized_url = config_with_password.get_sanitized_redis_url()
    assert "***" in sanitized_url, "Password should be sanitized with ***"
    assert (
        "secret123" not in sanitized_url
    ), "Actual password should not appear in sanitized URL"


def test_redis_connection_url_property():
    """Verify redis_connection_url property for actual connections."""

    from universal_framework.config.workflow_config import WorkflowConfig

    config = WorkflowConfig()

    # Verify property exists
    assert hasattr(
        config, "redis_connection_url"
    ), "WorkflowConfig must have redis_connection_url property"

    # Test REDIS_URL takes precedence
    config_with_url = WorkflowConfig(redis_url="redis://custom-host:6380/1")
    assert config_with_url.redis_connection_url == "redis://custom-host:6380/1"

    # Test component-based URL building
    config_components = WorkflowConfig(
        redis_host="localhost", redis_port="6379", redis_db="0", redis_password="secret"
    )
    expected_url = "redis://:secret@localhost:6379/0"
    assert config_components.redis_connection_url == expected_url


def test_field_count_completeness():
    """Verify total number of configuration fields meets expectations."""

    from universal_framework.config.workflow_config import WorkflowConfig

    config_fields = fields(WorkflowConfig)
    field_names = [field.name for field in config_fields]

    # Verify minimum field count (should have at least 20 configuration fields)
    assert (
        len(field_names) >= 20
    ), f"WorkflowConfig should have at least 20 fields, found {len(field_names)}: {field_names}"

    # Verify no duplicate field names
    assert len(field_names) == len(
        set(field_names)
    ), "WorkflowConfig should not have duplicate field names"


def test_docstring_completeness():
    """Verify WorkflowConfig has proper documentation."""

    from universal_framework.config.workflow_config import WorkflowConfig

    assert WorkflowConfig.__doc__ is not None, "WorkflowConfig must have a docstring"
    assert (
        len(WorkflowConfig.__doc__.strip()) > 100
    ), "WorkflowConfig docstring should be comprehensive"

    # Check for key documentation elements
    docstring = WorkflowConfig.__doc__.lower()
    assert (
        "universal framework" in docstring
    ), "Docstring should mention Universal Framework"
    assert "redis" in docstring, "Docstring should mention Redis"
    assert "environment" in docstring, "Docstring should mention environment variables"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
# fmt: on
# fmt: on
