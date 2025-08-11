from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from universal_framework.compliance.audit_manager import EnterpriseAuditManager
from universal_framework.compliance.authorization_matrix import AgentAuthorizationMatrix
from universal_framework.compliance.exceptions import (
    ComplianceViolationError,
    UnauthorizedStateUpdateError,
)
from universal_framework.config.feature_flags import feature_flags
from universal_framework.contracts.state import UniversalWorkflowState


class SafeModeStateValidator:
    """Safe mode state validator with minimal compliance checks."""

    def __init__(self) -> None:
        """Initialize safe mode validator without enterprise dependencies."""
        pass

    def validate_state_update(
        self,
        state: UniversalWorkflowState,
        updates: dict[str, Any],
        source_agent: str,
        event: str,
        user_context: dict[str, Any] | None = None,
    ) -> bool:
        """Minimal validation in safe mode - always passes."""
        return True

    def pre_update_validation(
        self,
        state: UniversalWorkflowState,
        updates: dict[str, Any],
        source_agent: str,
    ) -> None:
        """No-op validation in safe mode."""
        pass

    def post_update_validation(
        self,
        state: UniversalWorkflowState,
        source_agent: str,
        event: str,
        user_context: dict[str, Any] | None = None,
    ) -> None:
        """No-op validation in safe mode."""
        pass


class FailClosedStateValidator:
    """Fail-closed state validation with enterprise audit."""

    def __init__(self, audit_manager: EnterpriseAuditManager) -> None:
        self.audit_manager = audit_manager
        # Only create authorization matrix if authorization is enabled
        if feature_flags.is_enabled("AUTHORIZATION_MATRIX"):
            self.authorization_matrix = AgentAuthorizationMatrix()
        else:
            self.authorization_matrix = None

    def validate_state_update(
        self,
        state: UniversalWorkflowState,
        updates: dict[str, Any],
        source_agent: str,
        event: str,
        user_context: dict[str, Any] | None = None,
    ) -> UniversalWorkflowState:
        if not source_agent or not event:
            raise ComplianceViolationError(
                "source_agent and event required for audit compliance",
                "missing_audit_context",
                {"source_agent": source_agent, "event": event},
            )

        if not updates:
            return state

        attempted_fields = set(updates.keys())

        # Only check authorization if authorization matrix is enabled
        if self.authorization_matrix:
            is_authorized, authorized_fields, unauthorized_fields = (
                self.authorization_matrix.validate_agent_authorization(
                    source_agent, attempted_fields
                )
            )

            if not is_authorized:
                # Defensive programming for LangGraph state conversion
                # Use defensive state access utilities for LangGraph state conversion
                from universal_framework.utils.state_access import safe_get_session_id

                session_id = safe_get_session_id(state)

                self.audit_manager.log_security_event(
                    session_id=session_id,
                    event_type="unauthorized_state_update",
                    source_agent=source_agent,
                    details={
                        "attempted_fields": list(attempted_fields),
                        "unauthorized_fields": list(unauthorized_fields),
                        "authorized_fields": list(authorized_fields),
                    },
                )
            raise UnauthorizedStateUpdateError(
                source_agent, list(unauthorized_fields), list(authorized_fields)
            )
        else:
            # Safe mode - skip authorization checks
            pass

        self._validate_business_rules(state, updates, source_agent)

        if "workflow_phase" in updates:
            # Defensive programming for LangGraph state conversion
            # Use defensive state access utilities for LangGraph state conversion
            from universal_framework.utils.state_access import safe_get_phase

            state_workflow_phase = safe_get_phase(state)

            self._validate_fsm_transition(
                state_workflow_phase, updates["workflow_phase"], source_agent
            )

        # Defensive programming for LangGraph state conversion
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import safe_get_session_id

        session_id = safe_get_session_id(state)
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import safe_get_audit_trail

        state_audit_trail = safe_get_audit_trail(state)

        audit_entry = self._create_audit_entry(
            source_agent, event, updates, session_id, user_context
        )

        compliance_updates = {
            **updates,
            "audit_trail": state_audit_trail + [audit_entry],
            "last_update_source": source_agent,
            "last_update_timestamp": datetime.now().isoformat(),
        }

        updated_state = state.model_copy(update=compliance_updates)

        # Use sync wrapper for audit logging to avoid async/sync mixing
        # Defensive programming for LangGraph state conversion
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import safe_get_session_id

        session_id = safe_get_session_id(state)

        self.audit_manager.log_state_update_sync(
            session_id=session_id,
            source_agent=source_agent,
            event=event,
            fields_updated=list(attempted_fields),
            audit_id=audit_entry["audit_id"],
        )

        return updated_state

    def _validate_business_rules(
        self, state: UniversalWorkflowState, updates: dict[str, Any], source_agent: str
    ) -> None:
        # Defensive programming for LangGraph state conversion
        # Use defensive state access utilities for LangGraph state conversion
        from universal_framework.utils.state_access import (
            safe_get_session_id,
            safe_get_user_id,
        )

        state_session_id = safe_get_session_id(state)
        state_user_id = safe_get_user_id(state)

        if "session_id" in updates and updates["session_id"] != state_session_id:
            raise ComplianceViolationError(
                "session_id is immutable after initialization",
                "immutable_field_violation",
                {"field": "session_id", "source_agent": source_agent},
            )
        if (
            "user_id" in updates
            and state_user_id
            and updates["user_id"] != state_user_id
        ):
            raise ComplianceViolationError(
                "user_id cannot be changed within active session",
                "user_id_change_violation",
                {"field": "user_id", "source_agent": source_agent},
            )
        if "audit_trail" in updates:
            if not isinstance(updates["audit_trail"], list):
                raise ComplianceViolationError(
                    "audit_trail must be list",
                    "audit_trail_format_violation",
                    {"source_agent": source_agent},
                )
            # Defensive programming for LangGraph state conversion
            # Use defensive state access utilities for LangGraph state conversion
            from universal_framework.utils.state_access import safe_get_audit_trail

            state_audit_trail = safe_get_audit_trail(state)

            if len(updates["audit_trail"]) < len(state_audit_trail):
                raise ComplianceViolationError(
                    "audit_trail is append-only",
                    "audit_trail_truncation_violation",
                    {"source_agent": source_agent},
                )

    def _validate_fsm_transition(
        self, current_phase: str, target_phase: str, source_agent: str
    ) -> None:
        VALID_TRANSITIONS = {
            "initialization": ["discovery"],
            "discovery": ["analysis", "generation"],
            "analysis": ["generation"],
            "generation": ["review"],
            "review": ["delivery", "generation"],
            "delivery": ["completion"],
            "completion": [],
        }
        curr = (
            current_phase.value
            if hasattr(current_phase, "value")
            else str(current_phase)
        )
        targ = (
            target_phase.value if hasattr(target_phase, "value") else str(target_phase)
        )
        phase_aliases = {"batch_discovery": "discovery"}
        curr = phase_aliases.get(curr, curr)
        targ = phase_aliases.get(targ, targ)
        if curr not in VALID_TRANSITIONS:
            raise ComplianceViolationError(
                f"Unknown workflow phase: {current_phase}",
                "invalid_fsm_state",
                {"current_phase": current_phase, "source_agent": source_agent},
            )
        if targ not in VALID_TRANSITIONS[curr]:
            raise ComplianceViolationError(
                f"Invalid FSM transition: {current_phase} -> {target_phase}",
                "invalid_fsm_transition",
                {
                    "current_phase": current_phase,
                    "target_phase": target_phase,
                    "valid_transitions": VALID_TRANSITIONS[curr],
                    "source_agent": source_agent,
                },
            )

    def _create_audit_entry(
        self,
        source_agent: str,
        event: str,
        updates: dict[str, Any],
        session_id: str,
        user_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        audit_id = str(uuid.uuid4())
        return {
            "audit_id": audit_id,
            "timestamp": datetime.now().isoformat(),
            "source_agent": source_agent,
            "event": event,
            "session_id": session_id,
            "fields_modified": list(updates.keys()),
            "compliance_metadata": {
                "validation_version": "fail_closed_v1.0",
                "authorization_validated": True,
                "business_rules_validated": True,
                "fsm_validated": True,
            },
            "user_context": user_context or {},
            "security_classification": "enterprise_audit",
        }
