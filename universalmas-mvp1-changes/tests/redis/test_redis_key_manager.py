"""
Test suite for Redis Key Management system
==========================================

Tests centralized key generation, collision prevention,
environment isolation, and enterprise-grade validation.
"""

import pytest

from universal_framework.redis.key_manager import KeyManagementError, RedisKeyManager


class TestRedisKeyManager:
    """Test suite for RedisKeyManager."""

    def test_default_initialization(self):
        """Test default key manager initialization."""
        key_manager = RedisKeyManager()
        assert key_manager.key_prefix == "universal_framework"
        assert key_manager.environment == "prod"
        assert key_manager.enable_key_hashing is False

    def test_custom_initialization(self):
        """Test custom key manager initialization."""
        key_manager = RedisKeyManager(
            key_prefix="custom_app", environment="test", enable_key_hashing=True
        )
        assert key_manager.key_prefix == "custom_app"
        assert key_manager.environment == "test"
        assert key_manager.enable_key_hashing is True

    def test_session_key_generation(self):
        """Test session key generation."""
        key_manager = RedisKeyManager(environment="test")
        session_id = "test_session_12345678"

        key = key_manager.session_key(session_id)
        assert key == "universal_framework:test:session:test_session_12345678"

    def test_session_key_with_hashing(self):
        """Test session key generation with hashing enabled."""
        key_manager = RedisKeyManager(environment="test", enable_key_hashing=True)
        session_id = "sensitive_session_12345678"

        key = key_manager.session_key(session_id)
        assert key.startswith("universal_framework:test:session:")
        assert "sensitive_session_12345678" not in key
        assert len(key.split(":")[-1]) == 16  # Hash length

    def test_workflow_key_generation(self):
        """Test workflow key generation."""
        key_manager = RedisKeyManager(environment="test")
        session_id = "test_session_12345678"
        workflow_phase = "discovery"

        key = key_manager.workflow_key(session_id, workflow_phase)
        assert (
            key == "universal_framework:test:workflow:test_session_12345678:discovery"
        )

    def test_agent_key_generation(self):
        """Test agent key generation."""
        key_manager = RedisKeyManager(environment="test")
        session_id = "test_session_12345678"
        agent_name = "email_agent"

        key = key_manager.agent_key(session_id, agent_name)
        assert key == "universal_framework:test:agent:test_session_12345678:email_agent"

    def test_audit_key_generation(self):
        """Test audit key generation."""
        key_manager = RedisKeyManager(environment="test")
        session_id = "test_session_12345678"
        timestamp = "2024-01-15T10:30:45.123456"

        key = key_manager.audit_key(session_id, timestamp)
        assert (
            key
            == "universal_framework:test:audit:test_session_12345678:2024-01-15T10_30_45_123456"
        )

    def test_audit_key_with_auto_timestamp(self):
        """Test audit key generation with automatic timestamp."""
        key_manager = RedisKeyManager(environment="test")
        session_id = "test_session_12345678"

        key = key_manager.audit_key(session_id)
        assert key.startswith("universal_framework:test:audit:test_session_12345678:")
        # Should contain a timestamp
        timestamp_part = key.split(":")[-1]
        assert len(timestamp_part) > 0

    def test_checkpoint_key_generation(self):
        """Test checkpoint key generation."""
        key_manager = RedisKeyManager(environment="test")
        session_id = "test_session_12345678"
        checkpoint_id = "checkpoint_001"

        key = key_manager.checkpoint_key(session_id, checkpoint_id)
        assert (
            key
            == "universal_framework:test:checkpoint:test_session_12345678:checkpoint_001"
        )

    def test_user_sessions_key_generation(self):
        """Test user sessions key generation."""
        key_manager = RedisKeyManager(environment="test")
        user_id = "user_123456"

        key = key_manager.user_sessions_key(user_id)
        assert key == "universal_framework:test:user_sessions:user_123456"

    def test_messages_key_generation(self):
        """Test messages key generation."""
        key_manager = RedisKeyManager(environment="test")
        session_id = "test_session_12345678"

        key = key_manager.messages_key(session_id)
        assert key == "universal_framework:test:messages:test_session_12345678"

    def test_state_key_generation(self):
        """Test state key generation."""
        key_manager = RedisKeyManager(environment="test")
        session_id = "test_session_12345678"

        key = key_manager.state_key(session_id)
        assert key == "universal_framework:test:state:test_session_12345678"

    def test_environment_isolation(self):
        """Test that different environments generate different keys."""
        session_id = "test_session_12345678"

        dev_manager = RedisKeyManager(environment="development")
        prod_manager = RedisKeyManager(environment="production")

        dev_key = dev_manager.session_key(session_id)
        prod_key = prod_manager.session_key(session_id)

        assert dev_key != prod_key
        assert "development" in dev_key
        assert "production" in prod_key

    def test_key_prefix_isolation(self):
        """Test that different prefixes generate different keys."""
        session_id = "test_session_12345678"

        app1_manager = RedisKeyManager(key_prefix="app1", environment="test")
        app2_manager = RedisKeyManager(key_prefix="app2", environment="test")

        app1_key = app1_manager.session_key(session_id)
        app2_key = app2_manager.session_key(session_id)

        assert app1_key != app2_key
        assert "app1" in app1_key
        assert "app2" in app2_key

    def test_session_id_validation(self):
        """Test session ID validation."""
        key_manager = RedisKeyManager()

        # Test empty session ID
        with pytest.raises(KeyManagementError, match="Session ID cannot be empty"):
            key_manager.session_key("")

        # Test short session ID
        with pytest.raises(KeyManagementError, match="Session ID too short"):
            key_manager.session_key("short")

        # Test session ID with colon
        with pytest.raises(KeyManagementError, match="cannot contain ':' character"):
            key_manager.session_key("session:with:colons")

        # Test session ID with invalid characters
        with pytest.raises(KeyManagementError, match="contains invalid characters"):
            key_manager.session_key("session@with#special!")

    def test_component_name_validation(self):
        """Test component name validation."""
        key_manager = RedisKeyManager()
        session_id = "valid_session_12345678"

        # Test empty component name
        with pytest.raises(KeyManagementError, match="workflow_phase cannot be empty"):
            key_manager.workflow_key(session_id, "")

        # Test component with colon
        with pytest.raises(KeyManagementError, match="cannot contain ':' character"):
            key_manager.agent_key(session_id, "agent:with:colons")

        # Test component with invalid characters
        with pytest.raises(KeyManagementError, match="contains invalid characters"):
            key_manager.workflow_key(session_id, "phase@with#special!")

    def test_key_configuration_validation(self):
        """Test key configuration validation."""
        # Test invalid key prefix
        with pytest.raises(
            KeyManagementError, match="Key prefix cannot contain ':' character"
        ):
            RedisKeyManager(key_prefix="invalid:prefix")

        # Test invalid environment
        with pytest.raises(
            KeyManagementError, match="Environment cannot contain ':' character"
        ):
            RedisKeyManager(environment="invalid:env")

        # Test invalid characters in prefix
        with pytest.raises(
            KeyManagementError, match="Key prefix contains invalid characters"
        ):
            RedisKeyManager(key_prefix="invalid@prefix")

    def test_key_format_validation(self):
        """Test key format validation."""
        key_manager = RedisKeyManager(environment="test")

        # Valid key
        valid_key = "universal_framework:test:session:test_session_12345678"
        assert key_manager.validate_key_format(valid_key) is True

        # Invalid prefix
        invalid_key = "wrong_prefix:test:session:test_session_12345678"
        assert key_manager.validate_key_format(invalid_key) is False

        # Invalid environment
        invalid_key = "universal_framework:prod:session:test_session_12345678"
        assert key_manager.validate_key_format(invalid_key) is False

    def test_key_metadata_extraction(self):
        """Test key metadata extraction."""
        key_manager = RedisKeyManager(environment="test")
        key = "universal_framework:test:session:test_session_12345678"

        metadata = key_manager.get_key_metadata(key)
        assert metadata["valid"] is True
        assert metadata["prefix"] == "universal_framework"
        assert metadata["environment"] == "test"
        assert metadata["key_type"] == "session"
        assert metadata["identifier"] == "test_session_12345678"

    def test_session_pattern_generation(self):
        """Test session pattern for SCAN operations."""
        key_manager = RedisKeyManager(environment="test")
        pattern = key_manager.session_pattern()
        assert pattern == "universal_framework:test:session:*"

    def test_workflow_pattern_generation(self):
        """Test workflow pattern for SCAN operations."""
        key_manager = RedisKeyManager(environment="test")
        pattern = key_manager.workflow_pattern()
        assert pattern == "universal_framework:test:workflow:*"

    def test_agent_pattern_generation(self):
        """Test agent pattern for SCAN operations."""
        key_manager = RedisKeyManager(environment="test")
        pattern = key_manager.agent_pattern()
        assert pattern == "universal_framework:test:agent:*"

    def test_extract_session_id_from_key(self):
        """Test session ID extraction from keys."""
        key_manager = RedisKeyManager(environment="test")

        # Valid session key
        session_key = "universal_framework:test:session:test_session_12345678"
        session_id = key_manager.extract_session_id_from_key(session_key)
        assert session_id == "test_session_12345678"

        # Invalid key type
        workflow_key = (
            "universal_framework:test:workflow:test_session_12345678:discovery"
        )
        session_id = key_manager.extract_session_id_from_key(workflow_key)
        assert session_id is None

        # Invalid key format
        invalid_key = "invalid:key:format"
        session_id = key_manager.extract_session_id_from_key(invalid_key)
        assert session_id is None

    def test_collision_prevention(self):
        """Test that similar inputs generate different keys."""
        key_manager = RedisKeyManager(environment="test")

        # Similar session IDs should generate different keys
        key1 = key_manager.session_key("user123_session1")
        key2 = key_manager.session_key("user123_session2")
        assert key1 != key2

        # Different key types with same ID should be different
        session_key = key_manager.session_key("test_id_12345678")
        state_key = key_manager.state_key("test_id_12345678")
        messages_key = key_manager.messages_key("test_id_12345678")

        assert session_key != state_key
        assert session_key != messages_key
        assert state_key != messages_key

    def test_enterprise_compliance(self):
        """Test enterprise compliance features."""
        key_manager = RedisKeyManager(
            key_prefix="enterprise_app",
            environment="production",
            enable_key_hashing=True,
        )

        session_id = "sensitive_data_session_12345678"

        # Key should not contain sensitive data when hashing is enabled
        key = key_manager.session_key(session_id)
        assert "sensitive_data_session" not in key
        assert key.startswith("enterprise_app:production:session:")

        # Audit trail key should include timestamp
        audit_key = key_manager.audit_key(session_id)
        assert audit_key.startswith("enterprise_app:production:audit:")

        # Key metadata should be extractable
        metadata = key_manager.get_key_metadata(key)
        assert metadata["valid"] is True
        assert metadata["key_type"] == "session"

    def test_backward_compatibility_key_format(self):
        """Test that new keys maintain compatibility with expected format."""
        key_manager = RedisKeyManager(environment="development")
        session_id = "legacy_session_12345678"

        # Generated key should follow expected pattern
        key = key_manager.session_key(session_id)
        parts = key.split(":")

        assert len(parts) == 4
        assert parts[0] == "universal_framework"  # prefix
        assert parts[1] == "development"  # environment
        assert parts[2] == "session"  # type
        assert parts[3] == session_id  # identifier

        # Key should be extractable
        extracted_id = key_manager.extract_session_id_from_key(key)
        assert extracted_id == session_id
