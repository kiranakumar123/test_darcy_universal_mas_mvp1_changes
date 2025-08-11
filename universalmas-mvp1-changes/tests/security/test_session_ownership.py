from uuid import uuid4

import pytest

from universal_framework.redis.session_storage import SessionStorage
from universal_framework.security.session_validator import SessionValidator


class FakeRedisAdapter:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}

    async def execute_command(self, command: str, *args, **kwargs):
        if command == "SETEX":
            key, _, value = args
            self.store[key] = value
            return True
        if command == "GET":
            key = args[0]
            return self.store.get(key)
        if command == "SADD":
            key, value = args
            self.sets.setdefault(key, set()).add(value)
            return 1
        if command == "EXPIRE":
            return True
        raise NotImplementedError(command)


@pytest.mark.asyncio
async def test_real_session_ownership_validation():
    adapter = FakeRedisAdapter()
    storage = SessionStorage(adapter)
    validator = SessionValidator()
    validator.set_session_storage(storage)

    session_id = str(uuid4())
    await storage.create_session(session_id, "user_a")

    assert await validator.validate_session_ownership(session_id, "user_a") is True
    assert await validator.validate_session_ownership(session_id, "user_b") is False
    assert await validator.validate_session_ownership(str(uuid4()), "user_a") is False


@pytest.mark.asyncio
async def test_session_hijacking_prevention():
    adapter = FakeRedisAdapter()
    storage = SessionStorage(adapter)
    validator = SessionValidator()
    validator.set_session_storage(storage)

    session_id = str(uuid4())
    await storage.create_session(session_id, "owner")

    hijack_attempt = await validator.validate_session_ownership(session_id, "attacker")
    assert hijack_attempt is False
