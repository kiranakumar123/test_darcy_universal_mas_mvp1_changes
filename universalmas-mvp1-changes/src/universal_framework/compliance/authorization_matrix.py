from __future__ import annotations

from enum import Enum


class StateFieldCategory(Enum):
    SESSION_MANAGEMENT = "session_management"
    CONVERSATION_STATE = "conversation_state"
    FSM_STATE = "fsm_state"
    REQUIREMENTS_DATA = "requirements_data"
    GENERATION_OUTPUTS = "generation_outputs"
    AUDIT_METADATA = "audit_metadata"


class AgentAuthorizationMatrix:
    """Defines which agents can modify which state fields"""

    FIELD_CATEGORIES: dict[str, StateFieldCategory] = {
        # Session Management Fields
        "session_id": StateFieldCategory.SESSION_MANAGEMENT,
        "user_id": StateFieldCategory.SESSION_MANAGEMENT,
        "auth_token": StateFieldCategory.SESSION_MANAGEMENT,
        # Conversation State Fields
        "messages": StateFieldCategory.CONVERSATION_STATE,
        "message_history": StateFieldCategory.CONVERSATION_STATE,
        "conversation_checkpoints": StateFieldCategory.CONVERSATION_STATE,
        # FSM State Fields
        "workflow_phase": StateFieldCategory.FSM_STATE,
        "current_node": StateFieldCategory.FSM_STATE,
        "phase_completion": StateFieldCategory.FSM_STATE,
        "can_advance": StateFieldCategory.FSM_STATE,
        # Requirements Data Fields
        "user_objective": StateFieldCategory.REQUIREMENTS_DATA,
        "email_requirements": StateFieldCategory.REQUIREMENTS_DATA,
        "context_data": StateFieldCategory.REQUIREMENTS_DATA,
        # Generation Output Fields
        "email_strategy": StateFieldCategory.GENERATION_OUTPUTS,
        "email_content": StateFieldCategory.GENERATION_OUTPUTS,
        "final_outputs": StateFieldCategory.GENERATION_OUTPUTS,
        # Audit Metadata Fields
        "audit_trail": StateFieldCategory.AUDIT_METADATA,
        "last_update_source": StateFieldCategory.AUDIT_METADATA,
        "last_update_timestamp": StateFieldCategory.AUDIT_METADATA,
        "error_info": StateFieldCategory.AUDIT_METADATA,  # Add error_info field
    }

    AGENT_PERMISSIONS: dict[str, set[StateFieldCategory]] = {
        "session_manager": {
            StateFieldCategory.SESSION_MANAGEMENT,
            StateFieldCategory.AUDIT_METADATA,
        },
        "context_initializer": {
            StateFieldCategory.CONVERSATION_STATE,
            StateFieldCategory.AUDIT_METADATA,
        },
        "batch_requirements_collector": {
            StateFieldCategory.CONVERSATION_STATE,
            StateFieldCategory.REQUIREMENTS_DATA,
            StateFieldCategory.FSM_STATE,
            StateFieldCategory.AUDIT_METADATA,
        },
        "email_workflow_orchestrator": {
            StateFieldCategory.FSM_STATE,
            StateFieldCategory.CONVERSATION_STATE,
            StateFieldCategory.REQUIREMENTS_DATA,
            StateFieldCategory.AUDIT_METADATA,
        },
        "strategy_generator": {
            StateFieldCategory.GENERATION_OUTPUTS,
            StateFieldCategory.FSM_STATE,
            StateFieldCategory.AUDIT_METADATA,
        },
        "strategy_confirmation_handler": {
            StateFieldCategory.CONVERSATION_STATE,
            StateFieldCategory.FSM_STATE,
            StateFieldCategory.AUDIT_METADATA,
        },
        "enhanced_email_generator": {
            StateFieldCategory.GENERATION_OUTPUTS,
            StateFieldCategory.FSM_STATE,
            StateFieldCategory.AUDIT_METADATA,
        },
        "debug_controller": {
            StateFieldCategory.FSM_STATE,
            StateFieldCategory.AUDIT_METADATA,
        },
        "workflow_controller": {
            StateFieldCategory.FSM_STATE,
            StateFieldCategory.CONVERSATION_STATE,
            StateFieldCategory.AUDIT_METADATA,
        },
    }

    @classmethod
    def get_authorized_fields(cls, agent_name: str) -> set[str]:
        if agent_name not in cls.AGENT_PERMISSIONS:
            return set()
        authorized_categories = cls.AGENT_PERMISSIONS[agent_name]
        authorized_fields: set[str] = set()
        for field_name, category in cls.FIELD_CATEGORIES.items():
            if category in authorized_categories:
                authorized_fields.add(field_name)
        return authorized_fields

    @classmethod
    def validate_agent_authorization(
        cls, agent_name: str, attempted_fields: set[str]
    ) -> tuple[bool, set[str], set[str]]:
        authorized_fields = cls.get_authorized_fields(agent_name)
        unauthorized_fields = attempted_fields - authorized_fields
        is_authorized = len(unauthorized_fields) == 0
        return is_authorized, authorized_fields, unauthorized_fields
