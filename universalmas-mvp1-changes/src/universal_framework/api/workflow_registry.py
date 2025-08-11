"""Dynamic workflow registry for routing requests."""

from __future__ import annotations

from typing import Any

from universal_framework.contracts.exceptions import APIValidationError
from universal_framework.redis.session_storage import SessionStorage
from universal_framework.workflow.builder import create_streamlined_workflow

# Placeholder use case configs


def get_ocm_communications_config() -> dict[str, Any]:
    return {}


def get_document_generation_config() -> dict[str, Any]:
    return {}


def get_data_analysis_config() -> dict[str, Any]:
    return {}


class WorkflowRegistry:
    """Registry of preconfigured workflows."""

    def __init__(self) -> None:
        self._configs: dict[str, dict[str, Any]] = {}
        self._initialize_configs()

    def _initialize_configs(self) -> None:
        self._configs = {
            "universal_general": {"use_real_agents": True, "enable_debug": False},
            "ocm_communications": {"use_real_agents": False, "enable_debug": False},
            "document_generation": {"use_real_agents": False, "enable_debug": False},
            "data_analysis": {"use_real_agents": False, "enable_debug": False},
            "content_creation": {"use_real_agents": True, "enable_debug": False},
            "process_design": {"use_real_agents": True, "enable_debug": False},
            "email_workflow": {"use_real_agents": True, "enable_debug": False},
        }

    def get_workflow(
        self, workflow_type: str, session_storage: SessionStorage | None = None
    ) -> Any:
        """Get workflow with validation and optional session storage."""
        # Validation from main branch
        if not workflow_type or not workflow_type.strip():
            raise APIValidationError(
                message="Workflow type cannot be empty",
                endpoint="get_workflow",
                parameter="workflow_type",
                context={"provided_value": repr(workflow_type)},
            )

        config = self._configs.get(workflow_type)
        if config is None:
            raise APIValidationError(
                message=f"Unsupported workflow type '{workflow_type}'",
                endpoint="get_workflow",
                parameter="workflow_type",
                context={
                    "provided_type": workflow_type,
                    "supported_types": list(self._configs.keys()),
                },
            )

        # Session storage integration from session propagation branch
        return create_streamlined_workflow(
            use_real_agents=config["use_real_agents"],
            enable_debug=config["enable_debug"],
            session_storage=session_storage,
        )

    def list_supported_types(self) -> list[str]:
        return list(self._configs.keys())


workflow_registry = WorkflowRegistry()
