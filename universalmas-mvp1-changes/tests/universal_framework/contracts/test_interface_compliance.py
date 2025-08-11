# ruff: noqa: UP006,UP035,UP045
import inspect
from abc import ABC
from typing import Any

import pytest
from langchain_core.messages import BaseMessage

from universal_framework.config.workflow_config import WorkflowConfig
from universal_framework.contracts.redis.interfaces import (
    MessageStoreInterface,
    RedisConnectionInterface,
    RedisSessionManagerInterface,
    SessionDataInterface,
)
from universal_framework.redis.connection import RedisConnectionAdapter

# Utility --------------------------------------------------------------


def get_interface_methods(interface_class: type[Any]) -> dict[str, inspect.Signature]:
    """Return mapping of abstract method names to their signatures."""
    abstract_methods = getattr(interface_class, "__abstractmethods__", set())
    return {
        name: inspect.signature(getattr(interface_class, name))
        for name in abstract_methods
    }


# Dummy Classes --------------------------------------------------------


class DummyRedisSessionManager(RedisSessionManagerInterface):
    async def create_session(
        self, session_id: str, user_id: str, use_case: str
    ) -> bool:
        raise NotImplementedError

    async def store_session_data(
        self, session_id: str, data: SessionDataInterface
    ) -> bool:
        raise NotImplementedError

    async def retrieve_session_data(
        self, session_id: str
    ) -> SessionDataInterface | None:
        raise NotImplementedError

    async def update_session_activity(self, session_id: str) -> bool:
        raise NotImplementedError

    async def extend_session_ttl(self, session_id: str, hours: int = 24) -> bool:
        raise NotImplementedError

    async def cleanup_expired_sessions(self) -> int:
        raise NotImplementedError

    async def get_session_stats(self) -> dict[str, Any]:
        raise NotImplementedError

    async def get_active_sessions(self, user_id: str | None = None) -> list[str]:
        raise NotImplementedError


class DummyRedisConnection(RedisConnectionInterface):
    async def connect(self) -> bool:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError

    async def is_healthy(self) -> bool:
        raise NotImplementedError

    async def ping(self) -> bool:
        raise NotImplementedError

    async def get_info(self) -> dict[str, Any]:
        raise NotImplementedError


class DummySessionData(SessionDataInterface):
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionDataInterface":
        raise NotImplementedError

    def validate(self) -> list[str]:
        raise NotImplementedError


class DummyMessageStore(MessageStoreInterface):
    async def store_messages(
        self, session_id: str, messages: list[BaseMessage]
    ) -> bool:
        raise NotImplementedError

    async def retrieve_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[BaseMessage]:
        raise NotImplementedError

    async def append_message(self, session_id: str, message: BaseMessage) -> bool:
        raise NotImplementedError

    async def get_message_count(self, session_id: str) -> int:
        raise NotImplementedError


# Tests ----------------------------------------------------------------


@pytest.mark.parametrize(
    "interface_class,dummy_class",
    [
        (RedisSessionManagerInterface, DummyRedisSessionManager),
        (RedisConnectionInterface, DummyRedisConnection),
        (SessionDataInterface, DummySessionData),
        (MessageStoreInterface, DummyMessageStore),
    ],
)
def test_interface_methods_exist_with_correct_signatures(
    interface_class: type[Any], dummy_class: type[Any]
) -> None:
    """Verify all abstract methods exist with exact signatures."""
    abstract_methods = get_interface_methods(interface_class)
    for name, sig in abstract_methods.items():
        assert hasattr(dummy_class, name), f"{name} missing in {dummy_class.__name__}"
        assert sig == inspect.signature(getattr(dummy_class, name))


@pytest.mark.parametrize(
    "interface_class,dummy_class",
    [
        (RedisSessionManagerInterface, DummyRedisSessionManager),
        (RedisConnectionInterface, DummyRedisConnection),
        (SessionDataInterface, DummySessionData),
        (MessageStoreInterface, DummyMessageStore),
    ],
)
@pytest.mark.asyncio
async def test_abstract_methods_raise_not_implemented(
    interface_class: type[Any], dummy_class: type[Any]
) -> None:
    instance = dummy_class()
    for name in interface_class.__abstractmethods__:
        method = getattr(instance, name)
        sig = inspect.signature(method)
        args: list[Any] = [
            None
            for p in sig.parameters.values()
            if p.name not in {"self", "cls"} and p.default is inspect._empty
        ]
        if inspect.iscoroutinefunction(method):
            with pytest.raises(NotImplementedError):
                await method(*args)
        else:
            with pytest.raises(NotImplementedError):
                method(*args)


def test_type_annotations_present() -> None:
    for interface in [
        RedisSessionManagerInterface,
        RedisConnectionInterface,
        SessionDataInterface,
        MessageStoreInterface,
    ]:
        for _name, sig in get_interface_methods(interface).items():
            for param in sig.parameters.values():
                if param.name in {"self", "cls"}:
                    continue
                assert param.annotation is not inspect._empty
            assert sig.return_annotation is not inspect._empty


def test_interfaces_subclass_abc() -> None:
    for interface in [
        RedisSessionManagerInterface,
        RedisConnectionInterface,
        SessionDataInterface,
        MessageStoreInterface,
    ]:
        assert issubclass(interface, ABC)
        assert interface.__module__ == "universal_framework.contracts.redis.interfaces"


def test_redis_connection_adapter_implements_interface() -> None:
    config = WorkflowConfig()
    adapter = RedisConnectionAdapter(config)
    assert isinstance(adapter, RedisConnectionInterface)
    for name in RedisConnectionInterface.__abstractmethods__:
        assert hasattr(adapter, name)


def test_contract_drift_detection() -> None:
    expected_session_methods = {
        "create_session",
        "store_session_data",
        "retrieve_session_data",
        "update_session_activity",
        "extend_session_ttl",
        "cleanup_expired_sessions",
        "get_session_stats",
        "get_active_sessions",
    }
    assert RedisSessionManagerInterface.__abstractmethods__ == expected_session_methods

    expected_connection_methods = {
        "connect",
        "disconnect",
        "is_healthy",
        "ping",
        "get_info",
    }
    assert RedisConnectionInterface.__abstractmethods__ == expected_connection_methods
