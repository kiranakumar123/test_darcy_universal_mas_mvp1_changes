import pytest

from universal_framework.api.workflow_registry import WorkflowRegistry
from universal_framework.contracts.exceptions import (
    AgentExecutionError,
    APIValidationError,
    StateValidationError,
)
from universal_framework.contracts.messages import (
    create_agent_message,
    extract_agent_messages,
)


def test_extract_agent_messages_invalid_agent() -> None:
    with pytest.raises(AgentExecutionError):
        extract_agent_messages([], " ")


def test_create_agent_message_validation() -> None:
    with pytest.raises(StateValidationError):
        create_agent_message("", "b", "c", None)


def test_workflow_registry_invalid_type() -> None:
    registry = WorkflowRegistry()
    with pytest.raises(APIValidationError):
        registry.get_workflow("unknown_workflow")
