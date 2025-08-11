from __future__ import annotations

import pytest

from universal_framework.compliance import (
    ComplianceViolationError,
    EnterpriseAuditManager,
    FailClosedStateValidator,
    PrivacySafeLogger,
    UnauthorizedStateUpdateError,
)
from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase


def create_test_validator() -> FailClosedStateValidator:
    audit_mgr = EnterpriseAuditManager(PrivacySafeLogger(), hash_salt="test")
    return FailClosedStateValidator(audit_mgr)


def create_test_state(**overrides) -> UniversalWorkflowState:
    defaults = {
        "session_id": "test_session_001",
        "user_id": "test_user",
        "auth_token": "token1234567",
        "workflow_phase": WorkflowPhase.BATCH_DISCOVERY,
        "audit_trail": [],
    }
    return UniversalWorkflowState(**{**defaults, **overrides})


def test_authorized_state_update() -> None:
    validator = create_test_validator()
    state = create_test_state()
    updated = validator.validate_state_update(
        state,
        updates={"workflow_phase": "analysis"},
        source_agent="email_workflow_orchestrator",
        event="phase_transition",
    )
    assert updated.workflow_phase == "analysis"
    assert len(updated.audit_trail) == 1


def test_unauthorized_state_update() -> None:
    validator = create_test_validator()
    state = create_test_state()
    with pytest.raises(UnauthorizedStateUpdateError):
        validator.validate_state_update(
            state,
            updates={"session_id": "new"},
            source_agent="strategy_generator",
            event="bad_update",
        )


def test_fsm_transition_validation() -> None:
    validator = create_test_validator()
    state = create_test_state(workflow_phase="initialization")
    updated = validator.validate_state_update(
        state,
        updates={"workflow_phase": "discovery"},
        source_agent="email_workflow_orchestrator",
        event="phase_transition",
    )
    assert updated.workflow_phase == "discovery"
    with pytest.raises(ComplianceViolationError):
        validator.validate_state_update(
            state,
            updates={"workflow_phase": "completion"},
            source_agent="email_workflow_orchestrator",
            event="invalid_transition",
        )
