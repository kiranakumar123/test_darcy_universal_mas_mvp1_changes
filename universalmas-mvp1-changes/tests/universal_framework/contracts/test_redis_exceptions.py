import sys
import types

sys.modules.setdefault("universal_framework.workflow", types.ModuleType("workflow"))
sys.modules["universal_framework.workflow"].create_streamlined_workflow = (
    lambda *a, **k: None
)
for name in [
    "universal_framework.contracts.redis.interfaces",
    "universal_framework.contracts.redis.validation",
    "universal_framework.contracts.redis.key_manager",
]:
    module = types.ModuleType(name)
    sys.modules.setdefault(name, module)
    if name.endswith("interfaces"):
        module.RedisSessionManagerInterface = object
        module.RedisConnectionInterface = object
        module.SessionDataInterface = object
        module.MessageStoreInterface = object
    elif name.endswith("validation"):
        module.SessionValidator = object
        module.SchemaValidator = object
        module.validate_session_data = lambda *a, **k: []
        module.validate_message_data = lambda *a, **k: []
    elif name.endswith("key_manager"):
        module.RedisKeyManager = object
        module.SessionKeyBuilder = object
        module.get_session_key = lambda *a, **k: ""
        module.get_message_key = lambda *a, **k: ""

from universal_framework.contracts.redis.exceptions import (  # noqa: E402
    RedisAuthError,
    RedisConnectionError,
    RedisError,
    RedisSerializationError,
    RedisTimeoutError,
    sanitize_error_message,
    sanitize_redis_url,
)


def test_exception_hierarchy() -> None:
    assert issubclass(RedisConnectionError, RedisError)
    assert issubclass(RedisTimeoutError, RedisError)
    assert issubclass(RedisAuthError, RedisError)
    assert issubclass(RedisSerializationError, RedisError)


def test_sanitize_redis_url() -> None:
    url_with_pass = "redis://:secret@localhost:6379/0"
    assert sanitize_redis_url(url_with_pass) == "redis://:***@localhost:6379/0"

    url_with_user = "redis://user:secret@localhost:6379/0"
    assert sanitize_redis_url(url_with_user) == "redis://user:***@localhost:6379/0"

    url_without_pass = "redis://localhost:6379/0"
    assert sanitize_redis_url(url_without_pass) == url_without_pass


def test_sanitize_error_message() -> None:
    message = "Failed to connect to redis://:secret@localhost:6379/0"
    sanitized = sanitize_error_message(message)
    assert "secret" not in sanitized
    assert "***" in sanitized

    message2 = "Error with redis://localhost:6379/0 during auth"
    sanitized2 = sanitize_error_message(message2, "redis://:pass@localhost:6379/0")
    assert "pass" not in sanitized2
    assert sanitized2 == message2
