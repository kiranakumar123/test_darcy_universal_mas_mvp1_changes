"""Agent-to-agent communication contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from langchain_core.messages import BaseMessage

from universal_framework.contracts.state import WorkflowPhase

from .exceptions import AgentExecutionError, StateValidationError


class AgentMessage(BaseMessage):
    """Structured message for inter-agent communication."""

    type: str = "agent"

    def __init__(
        self,
        content: str,
        agent_name: str,
        phase: WorkflowPhase,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(content=content, **kwargs)
        self.agent_name = agent_name
        self.phase = phase
        self.metadata = metadata or {}


def create_agent_message(
    from_agent: str,
    to_agent: str,
    content: str,
    phase: WorkflowPhase,
    data: dict[str, Any] | None = None,
) -> AgentMessage:
    """Create validated agent message."""
    if not from_agent or not from_agent.strip():
        raise StateValidationError(
            message="Sender agent name cannot be empty",
            field_name="from_agent",
            expected_value="non-empty str",
            actual_value=repr(from_agent),
        )

    if not to_agent or not to_agent.strip():
        raise StateValidationError(
            message="Recipient agent name cannot be empty",
            field_name="to_agent",
            expected_value="non-empty str",
            actual_value=repr(to_agent),
        )

    if not content:
        raise StateValidationError(
            message="Message content cannot be empty",
            field_name="content",
            expected_value="non-empty str",
            actual_value=repr(content),
        )

    return AgentMessage(
        content=content,
        agent_name=from_agent,
        phase=phase,
        metadata={
            "from_agent": from_agent,
            "to_agent": to_agent,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
            "message_id": f"{from_agent}_{to_agent}_{datetime.now().timestamp()}",
        },
    )


def extract_agent_messages(
    messages: list[BaseMessage],
    target_agent: str,
) -> list[AgentMessage]:
    """Extract messages targeted to specific agent."""
    if not target_agent or not target_agent.strip():
        raise AgentExecutionError(
            message="Agent name cannot be empty or whitespace",
            agent_name="unknown",
            execution_phase="message_extraction",
            context={"provided_name": repr(target_agent)},
        )

    if not isinstance(messages, list):
        raise StateValidationError(
            message="Messages must be a list of BaseMessage objects",
            field_name="messages",
            expected_value="List[BaseMessage]",
            actual_value=type(messages).__name__,
            context={"messages_type": str(type(messages))},
        )

    return [
        msg
        for msg in messages
        if isinstance(msg, AgentMessage)
        and msg.metadata.get("to_agent") == target_agent
    ]
