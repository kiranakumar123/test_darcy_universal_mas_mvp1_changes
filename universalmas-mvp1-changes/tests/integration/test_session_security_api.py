import asyncio
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from universal_framework.api.dependencies import get_session_storage
from universal_framework.api.main import app
from universal_framework.api.middleware import EnterpriseAuthMiddleware
from universal_framework.observability.langsmith_middleware import (
    LangSmithAPITracingMiddleware,
)
from universal_framework.redis.session_storage import SessionStorage


class DummyTrace:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture(autouse=True)
def disable_langsmith(monkeypatch):
    monkeypatch.setattr(
        "universal_framework.observability.langsmith_middleware.trace",
        lambda **_: DummyTrace(),
    )

    async def _no_dispatch(self, request, call_next):
        return await call_next(request)

    monkeypatch.setattr(LangSmithAPITracingMiddleware, "dispatch", _no_dispatch)

    async def _auth_bypass(self, request, call_next):
        request.state.user = {"user_id": "test_user"}
        return await call_next(request)

    monkeypatch.setattr(EnterpriseAuthMiddleware, "dispatch", _auth_bypass)


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
            return self.store.get(args[0])
        if command == "SADD":
            key, value = args
            self.sets.setdefault(key, set()).add(value)
            return 1
        if command == "EXPIRE":
            return True
        raise NotImplementedError(command)


@pytest.fixture()
def client_with_storage():
    adapter = FakeRedisAdapter()
    storage = SessionStorage(adapter)
    app.dependency_overrides[get_session_storage] = lambda: storage
    original_env = os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = "development"
    client = TestClient(app)
    yield client, storage
    app.dependency_overrides.clear()
    if original_env is None:
        os.environ.pop("ENVIRONMENT", None)
    else:
        os.environ["ENVIRONMENT"] = original_env


def test_session_security_full_api_flow(client_with_storage):
    client, storage = client_with_storage
    session_id = None

    resp_a = client.post(
        "/api/v1/workflow/execute",
        json={
            "session_id": session_id,
            "workflow_type": "document_generation",
            "message": "doc",
            "context": {"user_id": "user_a"},
        },
        headers={
            "Authorization": "Bearer eyJhbGciOiAibm9uZSJ9.eyJzdWIiOiAidXNlcl90ZXN0In0."
        },
    )
    assert resp_a.status_code == 200
    session_id = resp_a.json()["session_id"]

    resp_b = client.post(
        "/api/v1/workflow/execute",
        json={
            "session_id": session_id,
            "workflow_type": "document_generation",
            "message": "hack",
            "context": {"user_id": "user_b"},
        },
        headers={
            "Authorization": "Bearer eyJhbGciOiAibm9uZSJ9.eyJzdWIiOiAidXNlcl90ZXN0In0."
        },
    )
    assert resp_b.status_code >= 400


def test_session_creation_in_api(client_with_storage):
    client, storage = client_with_storage
    resp = client.post(
        "/api/v1/workflow/execute",
        json={
            "session_id": None,
            "workflow_type": "document_generation",
            "message": "hello",
            "context": {"user_id": "creator"},
        },
        headers={
            "Authorization": "Bearer eyJhbGciOiAibm9uZSJ9.eyJzdWIiOiAidXNlcl90ZXN0In0."
        },
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    assert asyncio.run(storage.validate_session_ownership(session_id, "creator"))


def test_empty_string_session(client_with_storage):
    client, storage = client_with_storage
    resp = client.post(
        "/api/v1/workflow/execute",
        json={
            "session_id": "",
            "workflow_type": "document_generation",
            "message": "hello",
            "context": {"user_id": "blanker"},
        },
        headers={
            "Authorization": "Bearer eyJhbGciOiAibm9uZSJ9.eyJzdWIiOiAidXNlcl90ZXN0In0."
        },
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    assert session_id
    assert asyncio.run(storage.validate_session_ownership(session_id, "blanker"))


def test_unknown_session_id(client_with_storage):
    client, _ = client_with_storage
    unknown = "123e4567-e89b-12d3-a456-426614174000"
    resp = client.post(
        "/api/v1/workflow/execute",
        json={
            "session_id": unknown,
            "workflow_type": "document_generation",
            "message": "hey",
            "context": {"user_id": "tester"},
        },
        headers={
            "Authorization": "Bearer eyJhbGciOiAibm9uZSJ9.eyJzdWIiOiAidXNlcl90ZXN0In0."
        },
    )
    assert resp.status_code == 404


def test_invalid_session_id_format(client_with_storage):
    client, _ = client_with_storage
    resp = client.post(
        "/api/v1/workflow/execute",
        json={
            "session_id": "invalid",
            "workflow_type": "document_generation",
            "message": "bad",
            "context": {"user_id": "tester"},
        },
        headers={
            "Authorization": "Bearer eyJhbGciOiAibm9uZSJ9.eyJzdWIiOiAidXNlcl90ZXN0In0."
        },
    )
    assert resp.status_code == 400


def test_api_graceful_degradation_development(client_with_storage):
    client, storage = client_with_storage
    storage.redis_adapter = None
    with patch.dict(
        os.environ, {"REDIS_GRACEFUL_DEGRADATION": "true", "ENVIRONMENT": "development"}
    ):
        storage.__init__(redis_adapter=None)
        resp = client.post(
            "/api/v1/workflow/execute",
            json={
                "session_id": None,
                "workflow_type": "document_generation",
                "message": "test",
                "context": {"user_id": "test_user"},
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


def test_api_strict_security_production(client_with_storage):
    client, storage = client_with_storage
    storage.redis_adapter = None
    with patch.dict(
        os.environ, {"REDIS_GRACEFUL_DEGRADATION": "false", "ENVIRONMENT": "production"}
    ):
        storage.__init__(redis_adapter=None)
        resp = client.post(
            "/api/v1/workflow/execute",
            json={
                "session_id": None,
                "workflow_type": "document_generation",
                "message": "test",
                "context": {"user_id": "test_user"},
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert resp.status_code >= 400
