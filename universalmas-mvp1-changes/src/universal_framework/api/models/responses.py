"""Pydantic response models for API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str  # JSON serialization compatible
    framework_available: bool
    components: dict[str, bool]


class StatusResponse(BaseModel):
    """Status check response model."""

    framework: dict[str, Any]
    api: dict[str, Any]
    workflow: dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    message: str
    timestamp: str  # JSON serialization compatible
    details: dict[str, Any] | None = None


class WorkflowRequest(BaseModel):
    """Basic workflow execution request model."""

    session_id: str | None = None
    message: str
    context: dict[str, Any] | None = None


class WorkflowResponse(BaseModel):
    """Basic workflow execution response model."""

    session_id: str
    response: str
    timestamp: str  # JSON serialization compatible
    status: str | None = (
        None  # Backend-only field (optional - not sent to frontend per user request)
    )


class WorkflowExecuteRequest(WorkflowRequest):
    """Hybrid execution request."""

    workflow_type: str
    target_deliverables: list[str] | None = None
    use_case: str | None = (
        None  # Optional field for email composition and other use cases
    )


class WorkflowExecuteResponse(WorkflowResponse):
    """Detailed execution response."""

    workflow_phase: str
    completion_percentage: float
    deliverables: dict[str, Any]
    execution_mode: str

    # Backend-only fields (optional - not sent to frontend per user request)
    execution_time_seconds: float | None = None
    success: bool | None = None
    task_id: str | None = None


class SessionStatusResponse(BaseModel):
    """Session status response model."""

    session_id: str
    workflow_phase: str
    completion_percentage: float
    current_node: str | None = None
    messages_count: int
    deliverables_ready: list[str]
    last_updated: str
