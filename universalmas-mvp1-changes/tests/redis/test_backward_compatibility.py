"""
Backward Compatibility Tests for Redis Key Management
====================================================

Ensures that the new RedisKeyManager maintains compatibility with
existing Redis data and can access keys created with old patterns.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock

from universal_framework.redis.connection import RedisConnectionAdapter
from universal_framework.redis.key_manager import RedisKeyManager
from universal_framework.redis.session_storage import SessionStorage


class TestBackwardCompatibility:
    """Test backward compatibility with existing Redis keys."""

    def setup_method(self):
        """Set up test fixtures."""
        self.redis_adapter = AsyncMock(spec=RedisConnectionAdapter)
        self.key_manager = RedisKeyManager(environment="development")
        self.session_storage = SessionStorage(
            redis_adapter=self.redis_adapter, key_manager=self.key_manager
        )
        self.session_id = "legacy_session_12345678"
        self.user_id = "legacy_user_123"

    def test_key_format_consistency(self):
        """Test that new keys follow expected format for compatibility."""
        # Generate keys with new system
        session_key = self.key_manager.session_key(self.session_id)

        # Key should follow the pattern: prefix:environment:type:identifier
        parts = session_key.split(":")
        assert len(parts) == 4
        assert parts[0] == "universal_framework"  # prefix
        assert parts[1] == "development"  # environment
        assert parts[2] == "session"  # type
        assert parts[3] == self.session_id  # identifier

        # Should be extractable
        extracted_id = self.key_manager.extract_session_id_from_key(session_key)
        assert extracted_id == self.session_id

    def test_legacy_key_pattern_recognition(self):
        """Test recognition of legacy key patterns."""
        # Simulate legacy key format (if different from current)
        legacy_key = f"session:{self.session_id}"  # Old hard-coded format
        new_key = self.key_manager.session_key(self.session_id)

        # New key should be different but still valid
        assert legacy_key != new_key
        assert self.key_manager.validate_key_format(new_key) is True

        # Legacy key would not validate under new system
        assert self.key_manager.validate_key_format(legacy_key) is False

    async def test_session_data_migration_compatibility(self):
        """Test that session data format remains compatible."""
        # Create session data in expected format
        session_data = {
            "user_id": self.user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "metadata": {"client_ip": "192.168.1.1", "user_agent": "test"},
        }

        # Configure mock to return this data
        self.redis_adapter.execute_command.return_value = json.dumps(session_data)

        # Retrieve using new system
        result = await self.session_storage.get_session_data(self.session_id)

        # Data structure should be identical
        assert result == session_data
        assert result["user_id"] == self.user_id
        assert "created_at" in result
        assert "last_accessed" in result
        assert "metadata" in result

    async def test_graceful_degradation_preservation(self):
        """Test that graceful degradation behavior is preserved."""
        # Test with Redis unavailable
        session_storage = SessionStorage(
            redis_adapter=None, key_manager=self.key_manager
        )

        # Should still work with memory fallback
        result = await session_storage.create_session(self.session_id, self.user_id)
        assert result is True

        # Session should exist in memory
        assert self.session_id in session_storage.memory_sessions
        assert session_storage.memory_sessions[self.session_id] == self.user_id

    def test_environment_configuration_compatibility(self):
        """Test environment configuration compatibility."""
        # Test different environment configurations
        environments = ["development", "test", "staging", "production"]

        for env in environments:
            key_manager = RedisKeyManager(environment=env)
            session_key = key_manager.session_key(self.session_id)

            # Key should contain environment
            assert env in session_key

            # Should be valid format
            assert key_manager.validate_key_format(session_key) is True

            # Should extract metadata correctly
            metadata = key_manager.get_key_metadata(session_key)
            assert metadata["valid"] is True
            assert metadata["environment"] == env

    async def test_ttl_behavior_compatibility(self):
        """Test that TTL behavior remains compatible."""
        # Create session with TTL
        metadata = {"test": "data"}
        self.redis_adapter.execute_command.return_value = True

        result = await self.session_storage.create_session(
            self.session_id, self.user_id, metadata
        )
        assert result is True

        # Check that TTL is set correctly (24 hours = 86400 seconds)
        calls = self.redis_adapter.execute_command.call_args_list
        setex_call = calls[0]
        assert setex_call[0][0] == "SETEX"
        assert setex_call[0][2] == 86400  # TTL in seconds

    async def test_user_sessions_index_compatibility(self):
        """Test user sessions index compatibility."""
        # Create session
        self.redis_adapter.execute_command.return_value = True

        await self.session_storage.create_session(self.session_id, self.user_id)

        # Check user sessions index operations
        calls = self.redis_adapter.execute_command.call_args_list

        # Should use SADD for user sessions index
        sadd_call = calls[1]
        assert sadd_call[0][0] == "SADD"

        # Should use EXPIRE for user sessions index
        expire_call = calls[2]
        assert expire_call[0][0] == "EXPIRE"
        assert expire_call[0][2] == 86400  # Same TTL

    def test_key_manager_default_initialization(self):
        """Test key manager default initialization compatibility."""
        # Default initialization should work
        default_key_manager = RedisKeyManager()

        # Should have sensible defaults
        assert default_key_manager.key_prefix == "universal_framework"
        assert default_key_manager.environment == "prod"
        assert default_key_manager.enable_key_hashing is False

        # Should generate valid keys
        key = default_key_manager.session_key(self.session_id)
        assert default_key_manager.validate_key_format(key) is True

    def test_session_storage_default_initialization(self):
        """Test session storage default initialization compatibility."""
        # Should work with just Redis adapter
        session_storage = SessionStorage(redis_adapter=self.redis_adapter)

        # Should create default key manager
        assert session_storage.key_manager is not None
        assert isinstance(session_storage.key_manager, RedisKeyManager)

        # Should work with both parameters
        custom_key_manager = RedisKeyManager(environment="test")
        session_storage = SessionStorage(
            redis_adapter=self.redis_adapter, key_manager=custom_key_manager
        )
        assert session_storage.key_manager == custom_key_manager

    async def test_error_message_format_compatibility(self):
        """Test that error messages remain informative."""
        # Configure Redis to fail
        self.redis_adapter.execute_command.side_effect = Exception("Connection failed")

        # Try to create session
        try:
            await self.session_storage.create_session(self.session_id, self.user_id)
        except Exception as e:
            # Error should contain relevant information
            error_str = str(e)
            assert "session" in error_str.lower()
            assert self.session_id[:8] in error_str  # Truncated session ID

            # Should have context for debugging
            assert hasattr(e, "context")
            assert "session_id" in e.context
            assert "error" in e.context

    def test_metrics_and_logging_compatibility(self):
        """Test that metrics and logging behavior is preserved."""
        # Session storage should have logger
        assert self.session_storage.logger is not None

        # Should have expected configuration
        assert hasattr(self.session_storage, "session_ttl")
        assert self.session_storage.session_ttl == 24 * 60 * 60  # 24 hours

        # Should have graceful degradation configuration
        assert hasattr(self.session_storage, "allow_graceful_degradation")
        assert hasattr(self.session_storage, "environment")

    async def test_session_validation_logic_compatibility(self):
        """Test that session validation logic remains the same."""
        session_data = {
            "user_id": self.user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "metadata": {},
        }

        # Configure mock for successful validation
        self.redis_adapter.execute_command.side_effect = [
            json.dumps(session_data),  # GET call
            True,  # SETEX call for updating last_accessed
        ]

        # Validate session ownership
        result = await self.session_storage.validate_session_ownership(
            self.session_id, self.user_id
        )
        assert result is True

        # Should update last_accessed timestamp
        calls = self.redis_adapter.execute_command.call_args_list
        setex_call = calls[1]
        updated_data = json.loads(setex_call[0][3])
        assert "last_accessed" in updated_data

        # Timestamp should be recent
        last_accessed = datetime.fromisoformat(updated_data["last_accessed"])
        now = datetime.utcnow()
        assert (now - last_accessed).total_seconds() < 5  # Within 5 seconds

    def test_key_collision_prevention_compatibility(self):
        """Test that key collision prevention works across environments."""
        # Create key managers for different environments
        dev_manager = RedisKeyManager(environment="development")
        prod_manager = RedisKeyManager(environment="production")
        test_manager = RedisKeyManager(environment="test")

        # Same session ID should generate different keys
        dev_key = dev_manager.session_key(self.session_id)
        prod_key = prod_manager.session_key(self.session_id)
        test_key = test_manager.session_key(self.session_id)

        # All keys should be unique
        keys = [dev_key, prod_key, test_key]
        assert len(set(keys)) == len(keys)

        # Each should be valid in its own context
        assert dev_manager.validate_key_format(dev_key) is True
        assert prod_manager.validate_key_format(prod_key) is True
        assert test_manager.validate_key_format(test_key) is True

        # Should not be valid in other environments
        assert dev_manager.validate_key_format(prod_key) is False
        assert prod_manager.validate_key_format(dev_key) is False

    def test_redis_command_compatibility(self):
        """Test that Redis commands remain compatible."""
        # Key manager should generate keys compatible with Redis operations
        session_key = self.key_manager.session_key(self.session_id)
        user_sessions_key = self.key_manager.user_sessions_key(self.user_id)

        # Keys should not contain special Redis characters
        redis_special_chars = [" ", "\n", "\r", "\t"]
        for char in redis_special_chars:
            assert char not in session_key
            assert char not in user_sessions_key

        # Keys should be reasonable length for Redis
        assert len(session_key) < 250  # Redis practical limit
        assert len(user_sessions_key) < 250

        # Keys should be ASCII
        assert session_key.encode("ascii")
        assert user_sessions_key.encode("ascii")

    async def test_data_serialization_compatibility(self):
        """Test that data serialization remains compatible."""
        metadata = {
            "string_field": "test_value",
            "number_field": 12345,
            "boolean_field": True,
            "null_field": None,
            "list_field": [1, 2, 3],
            "dict_field": {"nested": "value"},
        }

        # Create session with complex metadata
        self.redis_adapter.execute_command.return_value = True

        await self.session_storage.create_session(
            self.session_id, self.user_id, metadata
        )

        # Check that data was serialized correctly
        calls = self.redis_adapter.execute_command.call_args_list
        setex_call = calls[0]
        serialized_data = setex_call[0][3]

        # Should be valid JSON
        session_data = json.loads(serialized_data)
        assert session_data["metadata"] == metadata
        assert session_data["user_id"] == self.user_id
