import pytest
from langchain_core.messages import BaseMessage

from universal_framework.contracts.exceptions import StateValidationError
from universal_framework.contracts.messages import (
    AgentMessage,
    create_agent_message,
    extract_agent_messages,
)
from universal_framework.contracts.state import (
    UniversalWorkflowState,
    WorkflowPhase,
)


def test_agent_message_creation() -> None:
    msg = create_agent_message(
        from_agent="agentA",
        to_agent="agentB",
        content="Hello!",
        phase=WorkflowPhase.STRATEGY_ANALYSIS,
        data={"foo": "bar"},
    )
    assert isinstance(msg, AgentMessage)
    assert msg.content == "Hello!"
    assert msg.agent_name == "agentA"
    assert msg.metadata["to_agent"] == "agentB"


def test_message_validation() -> None:
    with pytest.raises(StateValidationError):
        create_agent_message(
            "",
            "agentB",
            "content",
            WorkflowPhase.STRATEGY_ANALYSIS,
        )
    with pytest.raises(StateValidationError):
        create_agent_message(
            "agentA",
            "",
            "content",
            WorkflowPhase.STRATEGY_ANALYSIS,
        )
    with pytest.raises(StateValidationError):
        create_agent_message(
            "agentA",
            "agentB",
            "",
            WorkflowPhase.STRATEGY_ANALYSIS,
        )


def test_message_extraction() -> None:
    m1 = create_agent_message(
        "agentA",
        "agentB",
        "foo",
        WorkflowPhase.STRATEGY_ANALYSIS,
    )
    m2 = create_agent_message("agentC", "agentB", "bar", WorkflowPhase.REVIEW)
    m3 = create_agent_message("agentA", "agentD", "baz", WorkflowPhase.DELIVERY)
    all_msgs: list[BaseMessage] = [m1, m2, m3]
    filtered = extract_agent_messages(all_msgs, "agentB")
    assert len(filtered) == 2
    assert all(m.metadata["to_agent"] == "agentB" for m in filtered)


def test_integration_with_existing_state() -> None:
    s = UniversalWorkflowState(
        session_id="1",
        user_id="u",
        auth_token="t" * 10,
    )
    msg = create_agent_message(
        "a",
        "b",
        "msg",
        WorkflowPhase.STRATEGY_ANALYSIS,
    )
    s.messages.append(msg)
    assert isinstance(s.messages[0], AgentMessage)
