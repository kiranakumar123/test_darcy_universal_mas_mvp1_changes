import sys
import types

import pytest

# Stub external dependencies for isolated testing
sys.modules.setdefault("langchain.schema", types.ModuleType("langchain.schema"))
sys.modules["langchain.schema"].BaseMessage = type("BaseMessage", (), {})

sys.modules.setdefault(
    "langchain_core.messages", types.ModuleType("langchain_core.messages")
)
for name in ["BaseMessage", "AIMessage", "HumanMessage", "SystemMessage"]:
    setattr(
        sys.modules["langchain_core.messages"],
        name,
        type(name, (), {}),
    )

sys.modules.setdefault("pydantic", types.ModuleType("pydantic"))
sys.modules["pydantic"].BaseModel = type("BaseModel", (), {})
sys.modules["pydantic"].Field = lambda *a, **k: None

sys.modules.setdefault("pydantic.config", types.ModuleType("pydantic.config"))
sys.modules["pydantic.config"].ConfigDict = dict

sys.modules.setdefault("jsonschema", types.ModuleType("jsonschema"))
sys.modules["jsonschema"].validate = lambda *a, **k: None

sys.modules.setdefault("universal_framework.workflow", types.ModuleType("workflow"))
sys.modules["universal_framework.workflow"].create_streamlined_workflow = (
    lambda *a, **k: None
)

from universal_framework.contracts.redis.exceptions import (  # noqa: E402
    RedisKeyError,
    sanitize_error_message,
)
from universal_framework.contracts.redis.interfaces import (  # noqa: E402
    RedisSessionManagerInterface,
)
from universal_framework.contracts.redis.key_manager import (  # noqa: E402
    KeyType,
    RedisKeyManager,
    SessionKeyBuilder,
    configure_key_manager,
    get_message_key,
    get_session_key,
)


@pytest.fixture
def sample_session_ids():
    return ["session_alpha", "session_beta", "session_gamma"]


@pytest.fixture
def sample_components():
    return [
        KeyType.SESSION_MESSAGES,
        KeyType.SESSION_DATA,
        KeyType.SESSION_METADATA,
        KeyType.SESSION_CHECKPOINTS,
    ]


@pytest.fixture(autouse=True)
def reset_key_manager() -> None:
    """Ensure global key manager uses test configuration."""
    configure_key_manager("universal_framework", "dev")


def test_session_key_generation(sample_session_ids):
    configure_key_manager("universal_framework", "dev")
    for sid in sample_session_ids:
        key = get_session_key(KeyType.SESSION_MESSAGES, sid)
        assert key.startswith("session:universal_framework:dev:messages:")
        assert sid in key
        assert key.count(":") >= 5
        assert get_session_key(KeyType.SESSION_MESSAGES, sid) == key


def test_message_key_generation():
    session_a = "session_a_123"
    session_b = "session_b_456"
    key_a = get_message_key(session_a)
    key_b = get_message_key(session_b)
    assert session_a in key_a
    assert session_b in key_b
    assert key_a != key_b


def test_key_parsing_round_trip():
    manager = RedisKeyManager()
    builder = SessionKeyBuilder(manager)
    session_id = "test_session_123"
    original = builder.metadata_key(session_id)
    parsed = manager.parse_key(original)
    assert parsed["identifier"] == session_id
    assert parsed["key_type"] == "metadata"
    rebuilt = manager.build_session_key(KeyType.SESSION_METADATA, session_id)
    assert original == rebuilt


def test_session_isolation():
    manager = RedisKeyManager()
    builder = SessionKeyBuilder(manager)
    key_a = builder.data_key("alpha1234")
    key_b = builder.data_key("beta12345")
    assert key_a != key_b
    parsed_a = manager.parse_key(key_a)
    assert parsed_a["identifier"] == "alpha1234"
    assert parsed_a["identifier"] != "beta12345"


def test_malformed_key_handling():
    manager = RedisKeyManager()
    bad_keys = [
        "",
        "malformed",
        "no:session:id",
        "session:universal_framework:::v1",
        "../bad:path",
        "null\x00byte",
    ]
    for key in bad_keys:
        with pytest.raises(RedisKeyError):
            manager.parse_key(key)
        assert not manager.validate_key(key)


def test_key_sanitization_integration():
    try:
        RedisKeyManager().parse_key("bad_key")
    except RedisKeyError as exc:
        sanitized = sanitize_error_message(str(exc))
        assert "bad_key" in sanitized
        assert "password" not in sanitized


@pytest.mark.asyncio
async def test_session_manager_key_integration():
    class TestManager(RedisSessionManagerInterface):
        async def create_session(
            self, session_id: str, user_id: str, use_case: str
        ) -> bool:
            key = get_session_key(KeyType.SESSION_DATA, session_id)
            assert session_id in key
            return True

        async def store_session_data(self, session_id: str, data) -> bool:
            return True

        async def retrieve_session_data(self, session_id: str):
            return None

        async def update_session_activity(self, session_id: str) -> bool:
            return True

        async def extend_session_ttl(self, session_id: str, hours: int = 24) -> bool:
            return True

        async def cleanup_expired_sessions(self) -> int:
            return 0

        async def get_session_stats(self) -> dict:
            return {}

        async def get_active_sessions(self, user_id: str | None = None) -> list[str]:
            return []

    manager = TestManager()
    assert await manager.create_session("abc12345", "user", "test")


def test_hierarchical_key_pattern_compliance() -> None:
    """Verify keys follow the expected hierarchical pattern."""
    session_id = "test_session_123"
    component = KeyType.SESSION_MESSAGES.value

    key = get_session_key(KeyType.SESSION_MESSAGES, session_id)
    expected = f"session:universal_framework:dev:{component}:{session_id}:v1"
    assert key == expected

    parts = key.split(":")
    assert len(parts) == 6
    assert parts[0] == "session"
    assert parts[1] == "universal_framework"
    assert parts[2] == "dev"
    assert parts[3] == component
    assert parts[4] == session_id
    assert parts[5].startswith("v")


def test_comprehensive_session_isolation() -> None:
    """Verify complete session isolation across key types."""
    alpha = "session_alpha_enterprise"
    beta = "session_beta_enterprise"

    for key_type in [
        KeyType.SESSION_MESSAGES,
        KeyType.SESSION_DATA,
        KeyType.SESSION_METADATA,
        KeyType.SESSION_CHECKPOINTS,
    ]:
        key_a = get_session_key(key_type, alpha)
        key_b = get_session_key(key_type, beta)

        assert key_a != key_b

        parsed_a = RedisKeyManager().parse_key(key_a)
        parsed_b = RedisKeyManager().parse_key(key_b)

        assert parsed_a["identifier"] == alpha
        assert parsed_b["identifier"] == beta
        assert alpha not in parsed_b.values()
        assert beta not in parsed_a.values()


def test_cross_session_access_prevention() -> None:
    """Ensure sessions cannot access other session keys."""
    session_a = "confidential_session_a"
    session_b = "confidential_session_b"

    key_a = get_session_key(KeyType.SESSION_DATA, session_a)
    get_session_key(KeyType.SESSION_DATA, session_b)

    parsed_a = RedisKeyManager().parse_key(key_a)

    assert parsed_a["identifier"] == session_a
    for value in parsed_a.values():
        assert session_b not in str(value)


def test_all_key_types_follow_pattern() -> None:
    """Check that all builder methods use the same pattern."""
    manager = RedisKeyManager("universal_framework", "dev")
    builder = SessionKeyBuilder(manager)
    session_id = "structure_test_session"

    methods = [
        (builder.messages_key, "messages"),
        (builder.data_key, "data"),
        (builder.metadata_key, "metadata"),
        (builder.checkpoints_key, "checkpoints"),
    ]

    for method, component in methods:
        key = method(session_id)
        assert key.startswith(
            f"session:universal_framework:dev:{component}:{session_id}:v1"
        )
        parts = key.split(":")
        assert len(parts) == 6
        assert parts[4] == session_id


def test_key_format_validation_comprehensive() -> None:
    """Validate key format for multiple scenarios."""
    manager = RedisKeyManager("universal_framework", "dev")

    valid_keys = [
        "session:universal_framework:dev:messages:session_123:v1",
        "session:universal_framework:dev:data:user_session_456:v1",
        "session:universal_framework:dev:metadata:enterprise_session_789:v1",
        "session:universal_framework:dev:checkpoints:workflow_session_abc:v1",
    ]

    for key in valid_keys:
        assert manager.validate_key(key)
        parsed = manager.parse_key(key)
        assert "identifier" in parsed
        assert "key_type" in parsed

    invalid_keys = [
        "",
        "malformed",
        "wrong_prefix:session:component",
        "universal_framework:",
        "universal_framework:session:",
        ":universal_framework:session:comp",
        "universal_framework::session:comp",
        "universal_framework:session::comp",
    ]

    for key in invalid_keys:
        assert not manager.validate_key(key)
        with pytest.raises(RedisKeyError):
            manager.parse_key(key)


def test_security_boundary_enforcement() -> None:
    """Ensure malicious input is rejected by validation."""
    manager = RedisKeyManager()

    malicious_inputs = [
        "../../../etc/passwd",
        "session_id; DROP TABLE sessions;",
        "session\x00null_injection",
        "session_with_\r\n_newlines",
        "session_with_\t_tabs",
        "session_with_<script>_xss",
        "session_with_${jndi:ldap://evil}",
    ]

    for bad in malicious_inputs:
        assert not manager.validate_key(bad)
        with pytest.raises(RedisKeyError):
            manager.parse_key(bad)


def test_sensitive_data_protection() -> None:
    """Check sanitized errors for sensitive patterns."""
    session_id = "session_user_password_123_secret"

    key = get_session_key(KeyType.SESSION_DATA, session_id)
    assert session_id in key

    try:
        RedisKeyManager().parse_key("intentionally_bad_key")
    except RedisKeyError as exc:
        sanitized = sanitize_error_message(str(exc))
        for pattern in ["password", "secret", "token", "auth"]:
            assert pattern not in sanitized.lower()
        assert sanitized


@pytest.mark.asyncio
async def test_complete_contract_integration() -> None:
    """Exercise key generation through the full interface."""

    class ComprehensiveTestManager(RedisSessionManagerInterface):
        def __init__(self) -> None:
            self.log: list[str] = []

        async def create_session(
            self, session_id: str, user_id: str, use_case: str
        ) -> bool:
            key = get_session_key(KeyType.SESSION_DATA, session_id)
            self.log.append(f"create:{key}")
            assert session_id in key
            return True

        async def store_session_data(self, session_id: str, data) -> bool:
            data_key = get_session_key(KeyType.SESSION_DATA, session_id)
            meta_key = get_session_key(KeyType.SESSION_METADATA, session_id)
            self.log.extend([f"data:{data_key}", f"meta:{meta_key}"])
            assert data_key != meta_key
            return True

        async def retrieve_session_data(self, session_id: str):
            data_key = get_session_key(KeyType.SESSION_DATA, session_id)
            self.log.append(f"retrieve:{data_key}")
            return {"ok": True}

        async def update_session_activity(self, session_id: str) -> bool:
            return True

        async def extend_session_ttl(self, session_id: str, hours: int = 24) -> bool:
            return True

        async def cleanup_expired_sessions(self) -> int:
            return 0

        async def get_session_stats(self) -> dict:
            return {}

        async def get_active_sessions(self, user_id: str | None = None) -> list[str]:
            return []

    manager = ComprehensiveTestManager()
    session_id = "integration_test_session"

    await manager.create_session(session_id, "user", "email_generation")
    await manager.store_session_data(session_id, {"test": 1})
    await manager.retrieve_session_data(session_id)

    assert len(manager.log) >= 3
    for entry in manager.log:
        key = entry.split(":", 1)[1]
        assert key.startswith("session:universal_framework:dev:")
        assert session_id in key


def test_session_key_errors_and_suffix() -> None:
    manager = RedisKeyManager()

    with pytest.raises(RedisKeyError):
        manager.build_session_key(KeyType.SESSION_DATA, "short")

    with pytest.raises(RedisKeyError):
        manager.build_session_key(KeyType.SESSION_DATA, "")

    key = manager.build_session_key(
        KeyType.SESSION_MESSAGES,
        "validsess",
        suffix="extra",
    )
    assert key.endswith(":extra")


def test_user_and_global_key_generation() -> None:
    manager = RedisKeyManager("universal_framework", "prod")

    user_key = manager.build_user_key("user@example.com", "sessions")
    assert user_key.startswith("user:universal_framework:prod:")

    with pytest.raises(RedisKeyError):
        manager.build_user_key("")

    global_key = manager.build_global_key(KeyType.GLOBAL_STATS, "daily")
    assert global_key.startswith("global:universal_framework:prod:stats:daily")


def test_pattern_and_validation_branches() -> None:
    manager = RedisKeyManager()
    pattern = manager.get_pattern("session", "messages", "*")
    assert pattern.startswith("session:universal_framework:prod:messages:")

    key = manager.build_session_key(KeyType.SESSION_DATA, "validsess")
    assert manager.validate_key(key)

    mismatch_manager = RedisKeyManager("other", "prod")
    assert not mismatch_manager.validate_key(key)

    bad_version_key = "session:universal_framework:prod:data:abc:x1"
    assert not manager.validate_key(bad_version_key)

    missing_id_key = "session:universal_framework:prod:data::v1"
    assert not manager.validate_key(missing_id_key)


def test_user_sessions_key_builder() -> None:
    manager = RedisKeyManager()
    builder = SessionKeyBuilder(manager)
    key = builder.user_sessions_key("user1")
    assert key.startswith("user:universal_framework:prod:")
