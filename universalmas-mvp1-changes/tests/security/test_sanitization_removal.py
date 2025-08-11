import os
from uuid import UUID

import pytest
from fastapi import BackgroundTasks

os.environ.setdefault("OPENAI_API_KEY", "test")

from typing import Any

from universal_framework.api.main import execute_workflow
from universal_framework.api.models.responses import WorkflowRequest
from universal_framework.session.session_manager import EnterpriseSessionManager


class DummySessionManager(EnterpriseSessionManager):
    async def store_session_state(self, session_id: str, state: Any) -> bool:
        return True


@pytest.mark.asyncio
async def test_no_session_sanitization_in_main_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    async def fake_execute_workflow_hybrid(
        req: WorkflowRequest,
        background_tasks: BackgroundTasks,
        session_manager: EnterpriseSessionManager,
        session_storage: Any,
    ) -> WorkflowRequest:
        captured["session_id"] = req.session_id
        return req  # dummy

    monkeypatch.setattr(
        "universal_framework.api.main.execute_workflow_hybrid",
        fake_execute_workflow_hybrid,
    )

    request = WorkflowRequest(session_id=None, message="hi", context={})
    await execute_workflow(request, BackgroundTasks(), DummySessionManager())

    assert captured["session_id"] is not None
    assert not captured["session_id"].startswith("session_")
    UUID(captured["session_id"])  # valid UUID format
