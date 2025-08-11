import os
from unittest.mock import patch

import pytest

from universal_framework.redis.session_storage import SessionStorage


class TestSessionStorageGracefulDegradation:
    """Test graceful degradation behavior with environment variables."""

    def test_graceful_degradation_enabled_development(self):
        with patch.dict(
            os.environ,
            {"REDIS_GRACEFUL_DEGRADATION": "true", "ENVIRONMENT": "development"},
        ):
            storage = SessionStorage(redis_adapter=None)
            assert storage.allow_graceful_degradation is True
            assert storage.environment == "development"

    def test_graceful_degradation_disabled_production(self):
        with patch.dict(
            os.environ,
            {"REDIS_GRACEFUL_DEGRADATION": "false", "ENVIRONMENT": "production"},
        ):
            storage = SessionStorage(redis_adapter=None)
            assert storage.allow_graceful_degradation is False
            assert storage.environment == "production"

    @pytest.mark.asyncio
    async def test_session_validation_graceful_degradation_development(self):
        with patch.dict(
            os.environ,
            {"REDIS_GRACEFUL_DEGRADATION": "true", "ENVIRONMENT": "development"},
        ):
            storage = SessionStorage(redis_adapter=None)
            result = await storage.validate_session_ownership("test-session", "user")
            assert result is True

    @pytest.mark.asyncio
    async def test_session_validation_strict_security_production(self):
        with patch.dict(
            os.environ,
            {"REDIS_GRACEFUL_DEGRADATION": "false", "ENVIRONMENT": "production"},
        ):
            storage = SessionStorage(redis_adapter=None)
            result = await storage.validate_session_ownership("test-session", "user")
            assert result is False

    @pytest.mark.asyncio
    async def test_session_creation_graceful_degradation_development(self):
        with patch.dict(
            os.environ,
            {"REDIS_GRACEFUL_DEGRADATION": "true", "ENVIRONMENT": "development"},
        ):
            storage = SessionStorage(redis_adapter=None)
            result = await storage.create_session("test-session", "user", {})
            assert result is True

    @pytest.mark.asyncio
    async def test_session_creation_strict_security_production(self):
        with patch.dict(
            os.environ,
            {"REDIS_GRACEFUL_DEGRADATION": "false", "ENVIRONMENT": "production"},
        ):
            storage = SessionStorage(redis_adapter=None)
            result = await storage.create_session("test-session", "user", {})
            assert result is False

    def test_bool_env_parsing(self):
        with patch.dict(os.environ, {"REDIS_GRACEFUL_DEGRADATION": "true"}):
            assert SessionStorage().allow_graceful_degradation is True
        with patch.dict(os.environ, {"REDIS_GRACEFUL_DEGRADATION": "false"}):
            assert SessionStorage().allow_graceful_degradation is False
        with patch.dict(os.environ, {"REDIS_GRACEFUL_DEGRADATION": "1"}):
            assert SessionStorage().allow_graceful_degradation is True
        with patch.dict(os.environ, {"REDIS_GRACEFUL_DEGRADATION": "0"}):
            assert SessionStorage().allow_graceful_degradation is False

    @pytest.mark.asyncio
    async def test_environment_matrix_validation(self):
        environments = [
            ("development", True, True),
            ("testing", True, True),
            ("staging", True, True),
            ("production", True, False),
            ("development", False, False),
            ("production", False, False),
        ]
        for env, enabled, expected in environments:
            with patch.dict(
                os.environ,
                {
                    "REDIS_GRACEFUL_DEGRADATION": str(enabled).lower(),
                    "ENVIRONMENT": env,
                },
            ):
                storage = SessionStorage(redis_adapter=None)
                result = await storage.validate_session_ownership(
                    "test-session", "user"
                )
                assert result is expected, f"Failed for env={env}, graceful={enabled}"
