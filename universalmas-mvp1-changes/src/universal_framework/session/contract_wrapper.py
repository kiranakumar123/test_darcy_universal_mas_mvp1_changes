from __future__ import annotations

# ruff: noqa: UP006,UP045
from typing import Any

from universal_framework.observability import UniversalFrameworkLogger

from ..compliance.audit_manager import EnterpriseAuditManager
from ..compliance.classification import DataClassificationManager
from ..compliance.validators import enforce_contract
from ..config.feature_flags import feature_flags
from ..contracts.session.converters import (
    dict_to_workflow_state,
    workflow_state_to_dict,
)
from ..contracts.session.interfaces import (
    AuditTrailInterface,
    DataClassification,
    SessionManagerInterface,
)
from ..contracts.state import UniversalWorkflowState
from .session_manager import EnterpriseSessionManager


@enforce_contract(SessionManagerInterface)
class ContractEnterpriseSessionManager(SessionManagerInterface):
    """Wrapper adding classification and audit around EnterpriseSessionManager."""

    def __init__(
        self,
        manager: EnterpriseSessionManager,
        audit_manager: AuditTrailInterface | None = None,
    ) -> None:
        self.manager = manager
        if audit_manager is None:
            if feature_flags.is_enabled("ENTERPRISE_FEATURES"):
                from ..observability.enterprise_langsmith import (
                    EnterpriseLangSmithConfig,
                )

                privacy_logger = manager.privacy_logger if hasattr(manager, "privacy_logger") else None  # type: ignore[arg-type]
                langsmith_config = EnterpriseLangSmithConfig()
                self.audit_manager = EnterpriseAuditManager(
                    privacy_logger, langsmith_config
                )
            else:
                # Safe mode - use minimal audit interface
                from ..compliance.safe_mode import SafeModeAuditManager

                self.audit_manager = SafeModeAuditManager()
        else:
            self.audit_manager = audit_manager
        self.classification_manager = DataClassificationManager()
        self.logger = UniversalFrameworkLogger("contract_wrapper")

    async def store_session(
        self,
        session_id: str,
        data: dict[str, Any],
        classification: DataClassification = DataClassification.CONFIDENTIAL,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        ttl = self.classification_manager.get_ttl_for_classification(classification)
        audit_meta = {
            "operation": "store_session",
            "ttl": ttl,
            "classification": classification.value,
            "metadata": metadata or {},
        }
        audit_id = await self.audit_manager.log_operation(
            "store_session_start", session_id, audit_meta
        )
        try:
            workflow_state = dict_to_workflow_state(data)
            workflow_state = workflow_state.model_copy(
                update={"session_id": session_id}
            )
            result = await self.manager.store_session_state(session_id, workflow_state)
            audit_meta["result"] = result
            audit_meta["audit_id"] = audit_id
            await self.audit_manager.log_operation(
                "store_session_complete", session_id, audit_meta
            )
            return result
        except Exception as e:  # noqa: BLE001
            audit_meta["error"] = str(e)
            audit_meta["audit_id"] = audit_id
            await self.audit_manager.log_operation(
                "store_session_error", session_id, audit_meta
            )
            raise

    async def store_session_state(
        self, session_id: str, state: UniversalWorkflowState
    ) -> bool:
        """Store session state directly using the underlying manager.

        Args:
            session_id: The session identifier
            state: The workflow state to store

        Returns:
            bool: True if storage was successful
        """
        audit_id = await self.audit_manager.log_operation(
            "store_session_state_start", session_id, {}
        )
        audit_meta = {
            "operation": "store_session_state",
            "session_id": session_id,
            "state_phase": (
                state.workflow_phase.value
                if hasattr(state, "workflow_phase")
                else "unknown"
            ),
        }
        try:
            result = await self.manager.store_session_state(session_id, state)
            audit_meta["result"] = result
            audit_meta["audit_id"] = audit_id
            await self.audit_manager.log_operation(
                "store_session_state_complete", session_id, audit_meta
            )
            return result
        except Exception as e:  # noqa: BLE001
            audit_meta["error"] = str(e)
            audit_meta["audit_id"] = audit_id
            await self.audit_manager.log_operation(
                "store_session_state_error", session_id, audit_meta
            )
            raise

    async def retrieve_session(self, session_id: str) -> dict[str, Any] | None:
        audit_id = await self.audit_manager.log_operation(
            "retrieve_session_start", session_id, {}
        )
        try:
            state = await self.manager.get_session_state(session_id)
            result = workflow_state_to_dict(state) if state else None
            await self.audit_manager.log_operation(
                "retrieve_session_complete",
                session_id,
                {"audit_id": audit_id, "found": result is not None},
            )
            return result
        except Exception as e:  # noqa: BLE001
            await self.audit_manager.log_operation(
                "retrieve_session_error",
                session_id,
                {"audit_id": audit_id, "error": str(e)},
            )
            raise

    async def get_session_state(self, session_id: str) -> UniversalWorkflowState | None:
        """Get session state directly as UniversalWorkflowState object.

        Args:
            session_id: The session identifier

        Returns:
            Optional[UniversalWorkflowState]: The workflow state if found, None otherwise
        """
        audit_id = await self.audit_manager.log_operation(
            "get_session_state_start", session_id, {}
        )
        try:
            state = await self.manager.get_session_state(session_id)
            await self.audit_manager.log_operation(
                "get_session_state_complete",
                session_id,
                {"audit_id": audit_id, "found": state is not None},
            )
            return state
        except Exception as e:  # noqa: BLE001
            await self.audit_manager.log_operation(
                "get_session_state_error",
                session_id,
                {"audit_id": audit_id, "error": str(e)},
            )
            raise

    async def delete_session(self, session_id: str) -> bool:
        audit_id = await self.audit_manager.log_operation(
            "delete_session_start", session_id, {}
        )
        try:
            success = await self.manager.delete_session(session_id)
            await self.audit_manager.log_operation(
                "delete_session_complete",
                session_id,
                {"success": success, "audit_id": audit_id},
            )
            return success
        except Exception as e:  # noqa: BLE001
            await self.audit_manager.log_operation(
                "delete_session_error",
                session_id,
                {"audit_id": audit_id, "error": str(e)},
            )
            raise

    async def list_sessions(self, user_id: str | None = None) -> list[str]:
        await self.audit_manager.log_operation(
            "list_sessions_start", "*", {"user_id": user_id}
        )
        try:
            session_ids = await self.manager.list_sessions(user_id)
            await self.audit_manager.log_operation(
                "list_sessions_complete",
                "*",
                {"count": len(session_ids), "user_id": user_id},
            )
            return session_ids
        except Exception as e:  # noqa: BLE001
            await self.audit_manager.log_operation(
                "list_sessions_error", "*", {"error": str(e), "user_id": user_id}
            )
            raise
