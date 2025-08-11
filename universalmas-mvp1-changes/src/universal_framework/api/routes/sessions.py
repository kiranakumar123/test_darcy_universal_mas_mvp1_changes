from __future__ import annotations

# ruff: noqa: B008
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from universal_framework.api.dependencies import get_session_manager
from universal_framework.api.models.responses import SessionStatusResponse
from universal_framework.contracts.state import WorkflowPhase
from universal_framework.session.session_manager import EnterpriseSessionManager

router = APIRouter(prefix="/api/v1", tags=["sessions"])


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    session_manager: EnterpriseSessionManager = Depends(
        get_session_manager
    ),  # noqa: B008
) -> SessionStatusResponse:
    """Return workflow session status."""
    try:
        state = await session_manager.get_session_state(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="session_not_found")

        # Defensive programming for LangGraph state conversion
        try:
            phase_completion = state.phase_completion
            workflow_phase = state.workflow_phase
        except AttributeError:
            phase_completion = (
                state.get("phase_completion", {}) if isinstance(state, dict) else {}
            )
            workflow_phase = (
                WorkflowPhase(
                    state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
                )
                if isinstance(state, dict)
                else WorkflowPhase.INITIALIZATION
            )

        return SessionStatusResponse(
            session_id=session_id,
            workflow_phase=workflow_phase,
            completion_percentage=phase_completion.get(workflow_phase, 0.0),
            current_node=(
                state.context_data
                if hasattr(state, "context_data")
                else state.get("context_data", {})
            ).get("current_node"),
            messages_count=len(
                state.messages
                if hasattr(state, "messages")
                else state.get("messages", [])
            ),
            deliverables_ready=list(
                (
                    state.component_outputs
                    if hasattr(state, "component_outputs")
                    else state.get("component_outputs", {})
                ).keys()
            ),
            last_updated=(
                state.context_data
                if hasattr(state, "context_data")
                else state.get("context_data", {})
            ).get("last_updated", datetime.now().isoformat()),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
