"""
Integration tests for SessionStorage with RedisKeyManager
========================================================

Tests the complete integration of centralized key management
with session storage operations.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from universal_framework.redis.connection import RedisConnectionAdapter
from universal_framework.redis.exceptions import (
    SessionNotFoundError,
    SessionRetrievalError,
)
from universal_framework.redis.key_manager import RedisKeyManager
from universal_framework.redis.session_storage import SessionStorage


class TestSessionStorageIntegration:
    """Integration tests for SessionStorage with RedisKeyManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.redis_adapter = AsyncMock(spec=RedisConnectionAdapter)
        self.key_manager = RedisKeyManager(environment="test")
        self.session_storage = SessionStorage(
            redis_adapter=self.redis_adapter, key_manager=self.key_manager
        )
        self.session_id = "test_session_12345678"
        self.user_id = "test_user_123"

    async def test_create_session_with_key_manager(self):
        """Test session creation uses RedisKeyManager."""
        metadata = {"client_ip": "192.168.1.1"}

        # Configure mock
        self.redis_adapter.execute_command.return_value = True

        # Execute
        result = await self.session_storage.create_session(
            self.session_id, self.user_id, metadata
        )

        # Verify
        assert result is True

        # Check that RedisKeyManager-generated keys were used
        expected_session_key = self.key_manager.session_key(self.session_id)
        expected_user_sessions_key = self.key_manager.user_sessions_key(self.user_id)

        calls = self.redis_adapter.execute_command.call_args_list

        # First call: SETEX for session data
        setex_call = calls[0]
        assert setex_call[0][0] == "SETEX"
        assert setex_call[0][1] == expected_session_key
        assert setex_call[0][2] == 86400  # TTL

        # Parse session data
        session_data = json.loads(setex_call[0][3])
        assert session_data["user_id"] == self.user_id
        assert session_data["metadata"] == metadata

        # Second call: SADD for user sessions index
        sadd_call = calls[1]
        assert sadd_call[0][0] == "SADD"
        assert sadd_call[0][1] == expected_user_sessions_key
        assert sadd_call[0][2] == self.session_id

    async def test_session_exists_with_key_manager(self):
        """Test session existence check uses RedisKeyManager."""
        # Configure mock
        self.redis_adapter.execute_command.return_value = 1

        # Execute
        result = await self.session_storage.session_exists(self.session_id)

        # Verify
        assert result is True

        # Check correct key was used
        expected_key = self.key_manager.session_key(self.session_id)
        self.redis_adapter.execute_command.assert_called_once_with(
            "EXISTS", expected_key
        )

    async def test_validate_session_ownership_with_key_manager(self):
        """Test session ownership validation uses RedisKeyManager."""
        session_data = {
            "user_id": self.user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "metadata": {},
        }

        # Configure mock
        self.redis_adapter.execute_command.side_effect = [
            json.dumps(session_data),  # GET call
            True,  # SETEX call for updating last_accessed
        ]

        # Execute
        result = await self.session_storage.validate_session_ownership(
            self.session_id, self.user_id
        )

        # Verify
        assert result is True

        # Check correct key was used
        expected_key = self.key_manager.session_key(self.session_id)

        calls = self.redis_adapter.execute_command.call_args_list

        # First call: GET
        get_call = calls[0]
        assert get_call[0][0] == "GET"
        assert get_call[0][1] == expected_key

        # Second call: SETEX for updating last_accessed
        setex_call = calls[1]
        assert setex_call[0][0] == "SETEX"
        assert setex_call[0][1] == expected_key

    async def test_validate_session_ownership_not_found(self):
        """Test session ownership validation when session not found."""
        # Configure mock
        self.redis_adapter.execute_command.return_value = None

        # Execute and verify exception
        with pytest.raises(SessionNotFoundError) as exc_info:
            await self.session_storage.validate_session_ownership(
                self.session_id, self.user_id
            )

        # Check exception details
        assert exc_info.value.session_id == self.session_id
        expected_key = self.key_manager.session_key(self.session_id)
        assert exc_info.value.redis_key == expected_key

    async def test_get_session_data_with_key_manager(self):
        """Test session data retrieval uses RedisKeyManager."""
        session_data = {
            "user_id": self.user_id,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {"test": "data"},
        }

        # Configure mock
        self.redis_adapter.execute_command.return_value = json.dumps(session_data)

        # Execute
        result = await self.session_storage.get_session_data(self.session_id)

        # Verify
        assert result == session_data

        # Check correct key was used
        expected_key = self.key_manager.session_key(self.session_id)
        self.redis_adapter.execute_command.assert_called_once_with("GET", expected_key)

    async def test_update_session_metadata_with_key_manager(self):
        """Test session metadata update uses RedisKeyManager."""
        existing_data = {
            "user_id": self.user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "metadata": {"existing": "data"},
        }

        new_metadata = {"new": "value", "updated": "field"}

        # Configure mock
        self.redis_adapter.execute_command.side_effect = [
            json.dumps(existing_data),  # GET call
            True,  # SETEX call
        ]

        # Execute
        result = await self.session_storage.update_session_metadata(
            self.session_id, new_metadata
        )

        # Verify
        assert result is True

        # Check calls
        expected_key = self.key_manager.session_key(self.session_id)
        calls = self.redis_adapter.execute_command.call_args_list

        # GET call
        get_call = calls[0]
        assert get_call[0][0] == "GET"
        assert get_call[0][1] == expected_key

        # SETEX call
        setex_call = calls[1]
        assert setex_call[0][0] == "SETEX"
        assert setex_call[0][1] == expected_key

        # Parse updated data
        updated_data = json.loads(setex_call[0][3])
        assert updated_data["metadata"]["existing"] == "data"
        assert updated_data["metadata"]["new"] == "value"
        assert updated_data["metadata"]["updated"] == "field"

    async def test_delete_session_with_key_manager(self):
        """Test session deletion uses RedisKeyManager."""
        # Configure mock
        self.redis_adapter.execute_command.side_effect = [
            1,  # DEL result
            True,  # SREM result
        ]

        # Execute
        result = await self.session_storage.delete_session(
            self.session_id, self.user_id
        )

        # Verify
        assert result is True

        # Check calls
        expected_session_key = self.key_manager.session_key(self.session_id)
        expected_user_sessions_key = self.key_manager.user_sessions_key(self.user_id)

        calls = self.redis_adapter.execute_command.call_args_list

        # DEL call
        del_call = calls[0]
        assert del_call[0][0] == "DEL"
        assert del_call[0][1] == expected_session_key

        # SREM call
        srem_call = calls[1]
        assert srem_call[0][0] == "SREM"
        assert srem_call[0][1] == expected_user_sessions_key
        assert srem_call[0][2] == self.session_id

    async def test_get_user_sessions_with_key_manager(self):
        """Test user sessions retrieval uses RedisKeyManager."""
        session_ids = ["session1", "session2", "session3"]

        # Configure mock
        self.redis_adapter.execute_command.return_value = session_ids

        # Execute
        result = await self.session_storage.get_user_sessions(self.user_id)

        # Verify
        assert result == session_ids

        # Check correct key was used
        expected_key = self.key_manager.user_sessions_key(self.user_id)
        self.redis_adapter.execute_command.assert_called_once_with(
            "SMEMBERS", expected_key
        )

    async def test_error_handling_includes_redis_keys(self):
        """Test that error messages include Redis keys for debugging."""
        # Configure mock to raise exception
        self.redis_adapter.execute_command.side_effect = Exception("Redis error")

        # Test session existence check
        with pytest.raises(SessionRetrievalError) as exc_info:
            await self.session_storage.session_exists(self.session_id)

        # Check error includes Redis key
        expected_key = self.key_manager.session_key(self.session_id)
        assert exc_info.value.redis_key == expected_key
        assert expected_key in str(exc_info.value.context)

    async def test_memory_fallback_without_redis(self):
        """Test memory fallback when Redis is unavailable."""
        session_storage = SessionStorage(
            redis_adapter=None, key_manager=self.key_manager
        )

        # Test session creation fallback
        result = await session_storage.create_session(self.session_id, self.user_id)
        assert result is True

        # Test session existence check
        result = await session_storage.session_exists(self.session_id)
        assert result is True

        # Test session ownership validation
        result = await session_storage.validate_session_ownership(
            self.session_id, self.user_id
        )
        assert result is True

    def test_key_manager_injection(self):
        """Test RedisKeyManager dependency injection."""
        custom_key_manager = RedisKeyManager(
            key_prefix="custom_app", environment="staging"
        )

        session_storage = SessionStorage(
            redis_adapter=self.redis_adapter, key_manager=custom_key_manager
        )

        assert session_storage.key_manager == custom_key_manager
        assert session_storage.key_manager.key_prefix == "custom_app"
        assert session_storage.key_manager.environment == "staging"

    def test_default_key_manager_creation(self):
        """Test default RedisKeyManager creation when not provided."""
        session_storage = SessionStorage(redis_adapter=self.redis_adapter)

        assert session_storage.key_manager is not None
        assert isinstance(session_storage.key_manager, RedisKeyManager)
        # Should use development environment by default
        assert session_storage.key_manager.environment == "development"

    async def test_enterprise_audit_trail_integration(self):
        """Test audit trail support through key manager."""
        audit_timestamp = "2024-01-15T10:30:45.123456"

        # Generate audit key
        audit_key = self.key_manager.audit_key(self.session_id, audit_timestamp)

        # Verify audit key format
        assert "audit" in audit_key
        assert self.session_id in audit_key or self.key_manager.enable_key_hashing
        assert audit_timestamp.replace(":", "_").replace(".", "_") in audit_key

    async def test_key_collision_prevention(self):
        """Test that different session operations generate unique keys."""
        # Generate different key types for same session
        session_key = self.key_manager.session_key(self.session_id)
        state_key = self.key_manager.state_key(self.session_id)
        messages_key = self.key_manager.messages_key(self.session_id)
        audit_key = self.key_manager.audit_key(self.session_id)

        # All keys should be different
        keys = [session_key, state_key, messages_key, audit_key]
        assert len(set(keys)) == len(keys)

        # All keys should contain session identifier or hash
        for key in keys:
            assert self.session_id in key or self.key_manager.enable_key_hashing

    async def test_environment_isolation_in_storage(self):
        """Test environment isolation in session storage."""
        dev_key_manager = RedisKeyManager(environment="development")
        prod_key_manager = RedisKeyManager(environment="production")

        dev_storage = SessionStorage(
            redis_adapter=self.redis_adapter, key_manager=dev_key_manager
        )
        prod_storage = SessionStorage(
            redis_adapter=self.redis_adapter, key_manager=prod_key_manager
        )

        # Same session ID should generate different keys
        dev_key = dev_storage.key_manager.session_key(self.session_id)
        prod_key = prod_storage.key_manager.session_key(self.session_id)

        assert dev_key != prod_key
        assert "development" in dev_key
        assert "production" in prod_key
