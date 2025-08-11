"""
Test Session Storage with Redis Key Manager Integration
=====================================================

Integration tests for SessionStorage using centralized RedisKeyManager.
Tests backward compatibility, error handling, and enterprise patterns.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.universal_framework.redis.connection import RedisConnectionAdapter
from src.universal_framework.redis.exceptions import (
    SessionNotFoundError,
    SessionRetrievalError,
    SessionStorageError,
)
from src.universal_framework.redis.key_manager import RedisKeyManager
from src.universal_framework.redis.session_storage import SessionStorage


class TestSessionStorageWithKeyManager:
    """Test SessionStorage integration with RedisKeyManager."""

    @pytest.fixture
    def mock_redis_adapter(self) -> AsyncMock:
        """Create mock Redis adapter."""
        adapter = AsyncMock(spec=RedisConnectionAdapter)
        return adapter

    @pytest.fixture
    def key_manager(self) -> RedisKeyManager:
        """Create test key manager."""
        return RedisKeyManager(environment="test")

    @pytest.fixture
    def session_storage(
        self, mock_redis_adapter: AsyncMock, key_manager: RedisKeyManager
    ) -> SessionStorage:
        """Create SessionStorage with mock dependencies."""
        return SessionStorage(redis_adapter=mock_redis_adapter, key_manager=key_manager)

    async def test_create_session_uses_key_manager(
        self,
        session_storage: SessionStorage,
        mock_redis_adapter: AsyncMock,
        key_manager: RedisKeyManager,
    ) -> None:
        """Test that create_session uses RedisKeyManager for key generation."""
        session_id = "test_session_12345"
        user_id = "test_user_67890"
        metadata = {"client_type": "web"}

        # Configure Redis adapter mock
        mock_redis_adapter.execute_command.return_value = None

        # Call create_session
        result = await session_storage.create_session(session_id, user_id, metadata)

        # Verify Redis commands called with manager-generated keys
        expected_session_key = key_manager.session_key(session_id)
        expected_user_sessions_key = key_manager.user_sessions_key(user_id)

        calls = mock_redis_adapter.execute_command.call_args_list

        # Should have 3 calls: SETEX for session, SADD for user sessions, EXPIRE for user sessions
        assert len(calls) == 3

        # Check SETEX call for session data
        setex_call = calls[0]
        assert setex_call[0][0] == "SETEX"
        assert setex_call[0][1] == expected_session_key
        assert setex_call[0][2] == session_storage.session_ttl

        # Verify session data structure
        session_data = json.loads(setex_call[0][3])
        assert session_data["user_id"] == user_id
        assert session_data["metadata"] == metadata
        assert "created_at" in session_data
        assert "last_accessed" in session_data

        # Check SADD call for user sessions index
        sadd_call = calls[1]
        assert sadd_call[0][0] == "SADD"
        assert sadd_call[0][1] == expected_user_sessions_key
        assert sadd_call[0][2] == session_id

        # Check EXPIRE call for user sessions TTL
        expire_call = calls[2]
        assert expire_call[0][0] == "EXPIRE"
        assert expire_call[0][1] == expected_user_sessions_key
        assert expire_call[0][2] == session_storage.session_ttl

        assert result is True

    async def test_session_exists_uses_key_manager(
        self,
        session_storage: SessionStorage,
        mock_redis_adapter: AsyncMock,
        key_manager: RedisKeyManager,
    ) -> None:
        """Test that session_exists uses RedisKeyManager for key generation."""
        session_id = "test_session_12345"

        # Configure Redis adapter mock
        mock_redis_adapter.execute_command.return_value = 1  # Session exists

        # Call session_exists
        result = await session_storage.session_exists(session_id)

        # Verify Redis command called with manager-generated key
        expected_session_key = key_manager.session_key(session_id)
        mock_redis_adapter.execute_command.assert_called_once_with(
            "EXISTS", expected_session_key
        )

        assert result is True

    async def test_validate_session_ownership_uses_key_manager(
        self,
        session_storage: SessionStorage,
        mock_redis_adapter: AsyncMock,
        key_manager: RedisKeyManager,
    ) -> None:
        """Test that validate_session_ownership uses RedisKeyManager."""
        session_id = "test_session_12345"
        user_id = "test_user_67890"

        # Mock session data
        session_data = {
            "user_id": user_id,
            "created_at": "2025-07-21T10:00:00",
            "last_accessed": "2025-07-21T10:00:00",
            "metadata": {},
        }

        # Configure Redis adapter mock
        mock_redis_adapter.execute_command.side_effect = [
            json.dumps(session_data),  # GET response
            None,  # SETEX response for last_accessed update
        ]

        # Call validate_session_ownership
        result = await session_storage.validate_session_ownership(session_id, user_id)

        # Verify Redis commands called with manager-generated key
        expected_session_key = key_manager.session_key(session_id)
        calls = mock_redis_adapter.execute_command.call_args_list

        assert len(calls) == 2

        # Check GET call
        get_call = calls[0]
        assert get_call[0][0] == "GET"
        assert get_call[0][1] == expected_session_key

        # Check SETEX call for last_accessed update
        setex_call = calls[1]
        assert setex_call[0][0] == "SETEX"
        assert setex_call[0][1] == expected_session_key

        assert result is True

    async def test_get_session_data_uses_key_manager(
        self,
        session_storage: SessionStorage,
        mock_redis_adapter: AsyncMock,
        key_manager: RedisKeyManager,
    ) -> None:
        """Test that get_session_data uses RedisKeyManager."""
        session_id = "test_session_12345"

        # Mock session data
        session_data = {
            "user_id": "test_user_67890",
            "created_at": "2025-07-21T10:00:00",
            "metadata": {"client_type": "mobile"},
        }

        # Configure Redis adapter mock
        mock_redis_adapter.execute_command.return_value = json.dumps(session_data)

        # Call get_session_data
        result = await session_storage.get_session_data(session_id)

        # Verify Redis command called with manager-generated key
        expected_session_key = key_manager.session_key(session_id)
        mock_redis_adapter.execute_command.assert_called_once_with(
            "GET", expected_session_key
        )

        assert result == session_data

    async def test_delete_session_uses_key_manager(
        self,
        session_storage: SessionStorage,
        mock_redis_adapter: AsyncMock,
        key_manager: RedisKeyManager,
    ) -> None:
        """Test that delete_session uses RedisKeyManager."""
        session_id = "test_session_12345"
        user_id = "test_user_67890"

        # Configure Redis adapter mock
        mock_redis_adapter.execute_command.side_effect = [
            1,
            None,
        ]  # DEL, SREM responses

        # Call delete_session
        result = await session_storage.delete_session(session_id, user_id)

        # Verify Redis commands called with manager-generated keys
        expected_session_key = key_manager.session_key(session_id)
        expected_user_sessions_key = key_manager.user_sessions_key(user_id)

        calls = mock_redis_adapter.execute_command.call_args_list
        assert len(calls) == 2

        # Check DEL call
        del_call = calls[0]
        assert del_call[0][0] == "DEL"
        assert del_call[0][1] == expected_session_key

        # Check SREM call
        srem_call = calls[1]
        assert srem_call[0][0] == "SREM"
        assert srem_call[0][1] == expected_user_sessions_key
        assert srem_call[0][2] == session_id

        assert result is True

    async def test_get_user_sessions_uses_key_manager(
        self,
        session_storage: SessionStorage,
        mock_redis_adapter: AsyncMock,
        key_manager: RedisKeyManager,
    ) -> None:
        """Test that get_user_sessions uses RedisKeyManager."""
        user_id = "test_user_67890"
        expected_sessions = ["session_1", "session_2", "session_3"]

        # Configure Redis adapter mock
        mock_redis_adapter.execute_command.return_value = expected_sessions

        # Call get_user_sessions
        result = await session_storage.get_user_sessions(user_id)

        # Verify Redis command called with manager-generated key
        expected_user_sessions_key = key_manager.user_sessions_key(user_id)
        mock_redis_adapter.execute_command.assert_called_once_with(
            "SMEMBERS", expected_user_sessions_key
        )

        assert result == expected_sessions


class TestSessionStorageErrorHandling:
    """Test error handling with proper exception types."""

    @pytest.fixture
    def mock_redis_adapter(self) -> AsyncMock:
        """Create mock Redis adapter."""
        return AsyncMock(spec=RedisConnectionAdapter)

    @pytest.fixture
    def session_storage(self, mock_redis_adapter: AsyncMock) -> SessionStorage:
        """Create SessionStorage with mock dependencies."""
        return SessionStorage(redis_adapter=mock_redis_adapter)

    async def test_create_session_redis_error_raises_session_storage_error(
        self, session_storage: SessionStorage, mock_redis_adapter: AsyncMock
    ) -> None:
        """Test that Redis errors during create_session raise SessionStorageError."""
        session_id = "test_session_12345"
        user_id = "test_user_67890"

        # Configure Redis adapter to raise exception
        mock_redis_adapter.execute_command.side_effect = Exception(
            "Redis connection failed"
        )

        # Call create_session and verify exception
        with pytest.raises(SessionStorageError) as exc_info:
            await session_storage.create_session(session_id, user_id)

        error = exc_info.value
        assert error.session_id == session_id
        assert error.operation == "create"
        assert "Redis connection failed" in str(error)
        assert error.context["user_id"] == user_id

    async def test_session_exists_redis_error_raises_session_retrieval_error(
        self, session_storage: SessionStorage, mock_redis_adapter: AsyncMock
    ) -> None:
        """Test that Redis errors during session_exists raise SessionRetrievalError."""
        session_id = "test_session_12345"

        # Configure Redis adapter to raise exception
        mock_redis_adapter.execute_command.side_effect = Exception("Redis timeout")

        # Call session_exists and verify exception
        with pytest.raises(SessionRetrievalError) as exc_info:
            await session_storage.session_exists(session_id)

        error = exc_info.value
        assert error.session_id == session_id
        assert "Redis timeout" in str(error)

    async def test_validate_session_ownership_session_not_found_raises_session_not_found_error(
        self, session_storage: SessionStorage, mock_redis_adapter: AsyncMock
    ) -> None:
        """Test that missing session raises SessionNotFoundError."""
        session_id = "missing_session_12345"
        user_id = "test_user_67890"

        # Configure Redis adapter to return None (session not found)
        mock_redis_adapter.execute_command.return_value = None

        # Call validate_session_ownership and verify exception
        with pytest.raises(SessionNotFoundError) as exc_info:
            await session_storage.validate_session_ownership(session_id, user_id)

        error = exc_info.value
        assert error.session_id == session_id
        assert "Session not found" in str(error)

    async def test_get_session_data_session_not_found_raises_session_not_found_error(
        self, session_storage: SessionStorage, mock_redis_adapter: AsyncMock
    ) -> None:
        """Test that missing session data raises SessionNotFoundError."""
        session_id = "missing_session_12345"

        # Configure Redis adapter to return None
        mock_redis_adapter.execute_command.return_value = None

        # Call get_session_data and verify exception
        with pytest.raises(SessionNotFoundError) as exc_info:
            await session_storage.get_session_data(session_id)

        error = exc_info.value
        assert error.session_id == session_id


class TestSessionStorageGracefulDegradation:
    """Test graceful degradation behavior without Redis."""

    @pytest.fixture
    def session_storage_no_redis(self) -> SessionStorage:
        """Create SessionStorage without Redis adapter."""
        return SessionStorage(redis_adapter=None)

    async def test_create_session_no_redis_development(
        self, session_storage_no_redis: SessionStorage
    ) -> None:
        """Test session creation without Redis in development environment."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            storage = SessionStorage(redis_adapter=None)

            result = await storage.create_session("test_session", "test_user")
            assert result is True
            assert "test_session" in storage.memory_sessions
            assert storage.memory_sessions["test_session"] == "test_user"

    async def test_session_exists_no_redis_uses_memory(
        self, session_storage_no_redis: SessionStorage
    ) -> None:
        """Test session_exists without Redis uses memory storage."""
        session_storage_no_redis.memory_sessions["test_session"] = "test_user"

        result = await session_storage_no_redis.session_exists("test_session")
        assert result is True

        result = await session_storage_no_redis.session_exists("missing_session")
        assert result is False

    async def test_delete_session_no_redis_uses_memory(
        self, session_storage_no_redis: SessionStorage
    ) -> None:
        """Test delete_session without Redis uses memory storage."""
        session_storage_no_redis.memory_sessions["test_session"] = "test_user"

        result = await session_storage_no_redis.delete_session(
            "test_session", "test_user"
        )
        assert result is True
        assert "test_session" not in session_storage_no_redis.memory_sessions

    async def test_get_user_sessions_no_redis_uses_memory(
        self, session_storage_no_redis: SessionStorage
    ) -> None:
        """Test get_user_sessions without Redis uses memory storage."""
        session_storage_no_redis.memory_sessions.update(
            {"session_1": "user_1", "session_2": "user_1", "session_3": "user_2"}
        )

        result = await session_storage_no_redis.get_user_sessions("user_1")
        assert sorted(result) == ["session_1", "session_2"]

        result = await session_storage_no_redis.get_user_sessions("user_2")
        assert result == ["session_3"]


class TestBackwardCompatibility:
    """Test backward compatibility with existing Redis data."""

    @pytest.fixture
    def legacy_key_manager(self) -> RedisKeyManager:
        """Create key manager that matches legacy key format."""
        # Legacy format was "session:{session_id}"
        # Our new format is "universal_framework:prod:session:{session_id}"
        return RedisKeyManager()

    async def test_can_read_data_with_new_keys(self) -> None:
        """Test that new implementation can read data created with new keys."""
        mock_adapter = AsyncMock()
        key_manager = RedisKeyManager(environment="test")
        storage = SessionStorage(redis_adapter=mock_adapter, key_manager=key_manager)

        session_id = "test_session_12345"
        session_data = {
            "user_id": "test_user",
            "created_at": "2025-07-21T10:00:00",
            "metadata": {},
        }

        # Mock Redis response with new key format
        mock_adapter.execute_command.return_value = json.dumps(session_data)

        result = await storage.get_session_data(session_id)

        # Verify correct key was used
        expected_key = key_manager.session_key(session_id)
        mock_adapter.execute_command.assert_called_with("GET", expected_key)
        assert result == session_data

    def test_key_format_migration_detection(self) -> None:
        """Test that key manager can detect and validate new vs legacy formats."""
        manager = RedisKeyManager()

        # New format keys should validate
        new_key = "universal_framework:prod:session:test_session_12345"
        assert manager.validate_key_format(new_key) is True

        # Legacy format keys should not validate with new manager
        legacy_key = "session:test_session_12345"
        assert manager.validate_key_format(legacy_key) is False

        # Can extract metadata from new format
        metadata = manager.get_key_metadata(new_key)
        assert metadata["valid"] is True
        assert metadata["key_type"] == "session"
        assert metadata["identifier"] == "test_session_12345"
