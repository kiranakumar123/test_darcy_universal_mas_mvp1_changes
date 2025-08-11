"""
Test fixtures for Universal Framework

Shared test data and utilities.
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase


@pytest.fixture
def sample_session_state():
    """Sample session state for testing"""
    return UniversalWorkflowState(
        session_id="test_session_123",
        user_id="test_user_456",
        auth_token="test_token_789",
        workflow_phase=WorkflowPhase.INITIALIZATION,
    )


@pytest.fixture
def sample_discovery_state():
    """Sample state in discovery phase"""
    return UniversalWorkflowState(
        session_id="test_session_123",
        user_id="test_user_456",
        auth_token="test_token_789",
        workflow_phase=WorkflowPhase.BATCH_DISCOVERY,
    )


@pytest.fixture
def sample_state_with_messages():
    """State pre-populated with a variety of messages."""
    messages = [
        HumanMessage(content="Need help with Q4 report"),
        AIMessage(content="Sure, gathering details"),
        HumanMessage(content="Make it concise"),
    ]
    base = UniversalWorkflowState(
        session_id="test_session_123",
        user_id="test_user_456",
        auth_token="test_token_789",
    )
    return base.copy(update={"messages": messages})


# Will be expanded as more fixtures are needed
__all__: list[str] = [
    "sample_session_state",
    "sample_discovery_state",
    "sample_state_with_messages",
]
