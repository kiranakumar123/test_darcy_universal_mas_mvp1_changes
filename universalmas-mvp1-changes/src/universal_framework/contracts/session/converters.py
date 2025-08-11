from __future__ import annotations

from typing import Any

from ..state import UniversalWorkflowState


def dict_to_workflow_state(data: dict[str, Any]) -> UniversalWorkflowState:
    """Convert dictionary to UniversalWorkflowState."""
    try:
        if isinstance(data, dict) and "session_id" in data:
            return UniversalWorkflowState.model_validate(data)
        return UniversalWorkflowState(
            session_id=data.get("session_id", "unknown"),
            user_id=data.get("user_id", "unknown"),
            auth_token=data.get("auth_token", "default"),
            context_data=data,
        )
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Cannot convert to workflow state: {exc}") from exc


def workflow_state_to_dict(state: UniversalWorkflowState) -> dict[str, Any]:
    """Convert UniversalWorkflowState to dictionary."""
    return state.model_dump()
