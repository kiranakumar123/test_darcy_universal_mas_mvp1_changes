"""
Conversation History Manager

This module provides utilities for extracting and formatting conversation history
from UniversalWorkflowState for use with SalesGPT-style LLMChain patterns.

Key Features:
- Exact SalesGPT conversation history formatting
- Defensive programming for state dict/object conversion
- Conversation context metadata extraction
- History truncation for performance optimization
- Backward compatibility with existing message formats

SalesGPT Pattern Compliance:
- Uses exact "User: {message} <END_OF_TURN>" format
- Implements "\n".join(history_entries) pattern
- Handles both Pydantic objects and dict states
- Provides conversation metadata for enhanced classification

Dependencies:
- langchain_core.messages: BaseMessage, HumanMessage, AIMessage
- UniversalWorkflowState: Framework state management
"""

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from universal_framework.observability import UniversalFrameworkLogger

from ..contracts.state import UniversalWorkflowState

# Initialize enterprise logger
logger = UniversalFrameworkLogger("conversation_history_manager")


class ConversationHistoryManager:
    """
    Manages conversation history extraction and formatting for LLM context injection.

    This class implements SalesGPT's exact conversation history formatting patterns:
    - "User: {message} <END_OF_TURN>" for user messages
    - "{agent_name}: {message} <END_OF_TURN>" for assistant messages
    - "\n".join(formatted_entries) for history concatenation

    Attributes:
        max_history_length: Maximum characters to include in history (for performance)
        include_agent_responses: Whether to include AI responses in history
    """

    def __init__(
        self, max_history_length: int = 2000, include_agent_responses: bool = True
    ):
        """
        Initialize conversation history manager.

        Args:
            max_history_length: Maximum characters to include in formatted history
            include_agent_responses: Whether to include AI responses in history
        """
        self.max_history_length = max_history_length
        self.include_agent_responses = include_agent_responses

    def extract_conversation_history(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> str:
        """
        Extract conversation history from state in exact SalesGPT format.

        This method implements SalesGPT's exact conversation history formatting:
        - User messages: "User: {content} <END_OF_TURN>"
        - AI messages: "{agent_name}: {content} <END_OF_TURN>"
        - Joined with "\n" exactly like SalesGPT

        Args:
            state: UniversalWorkflowState or dict containing messages

        Returns:
            str: Formatted conversation history ready for LLM prompt injection

        Example:
            >>> state = UniversalWorkflowState(messages=[
            ...     HumanMessage(content="Hello"),
            ...     AIMessage(content="Hi there")
            ... ])
            >>> manager.extract_conversation_history(state)
            'User: Hello <END_OF_TURN>\nAssistant: Hi there <END_OF_TURN>'
        """
        # Step 1: Defensive programming for LangGraph state conversion
        try:
            messages = state.messages
        except AttributeError:
            # Handle dict state (LangGraph conversion)
            messages = state.get("messages", [])

        if not messages:
            return ""

        # Step 2: Format messages according to SalesGPT pattern
        formatted_entries = []

        for message in messages:
            if isinstance(message, BaseMessage):
                # Handle LangChain message objects
                if isinstance(message, HumanMessage):
                    formatted_entries.append(f"User: {message.content} <END_OF_TURN>")
                elif isinstance(message, AIMessage) and self.include_agent_responses:
                    # Extract agent name from additional_kwargs or use default
                    agent_name = message.additional_kwargs.get(
                        "agent_name", "Assistant"
                    )
                    formatted_entries.append(
                        f"{agent_name}: {message.content} <END_OF_TURN>"
                    )
            elif isinstance(message, dict):
                # Handle dict message format (defensive programming)
                role = message.get("role", "User")
                content = message.get("content", "")
                if role == "user":
                    formatted_entries.append(f"User: {content} <END_OF_TURN>")
                elif role == "assistant" and self.include_agent_responses:
                    agent_name = message.get("agent_name", "Assistant")
                    formatted_entries.append(f"{agent_name}: {content} <END_OF_TURN>")
            else:
                # Fallback for unknown message types
                content = str(message)
                formatted_entries.append(f"User: {content} <END_OF_TURN>")

        # Step 3: Join with newlines (exact SalesGPT pattern)
        full_history = "\n".join(formatted_entries)

        # Step 4: Truncate if necessary for performance
        if len(full_history) > self.max_history_length:
            # Keep the most recent part of the conversation
            # Add ellipsis to indicate truncation
            truncated = "..." + full_history[-self.max_history_length + 3 :]
            return truncated

        return full_history

    def get_conversation_context_summary(
        self, state: UniversalWorkflowState | dict[str, Any]
    ) -> dict[str, Any]:
        """
        Extract conversation metadata for enhanced intent classification.

        Provides context indicators that help improve intent classification accuracy:
        - turn_count: Total number of messages
        - has_context: Whether conversation has history (>1 message)
        - recent_agent_responses: Number of AI responses in last 3 turns
        - user_message_count: Total user messages
        - conversation_length: Total character count

        Args:
            state: UniversalWorkflowState or dict containing messages

        Returns:
            Dict containing conversation statistics and context indicators

        Example:
            >>> summary = manager.get_conversation_context_summary(state)
            >>> summary["has_context"]  # True if conversation has history
            True
        """
        # Defensive programming for state access
        try:
            messages = state.messages
        except AttributeError:
            messages = state.get("messages", [])

        if not messages:
            return {
                "turn_count": 0,
                "has_context": False,
                "recent_agent_responses": 0,
                "user_message_count": 0,
                "conversation_length": 0,
            }

        # Count message types
        user_message_count = 0
        ai_message_count = 0
        conversation_length = 0

        for message in messages:
            if isinstance(message, BaseMessage):
                if isinstance(message, HumanMessage):
                    user_message_count += 1
                elif isinstance(message, AIMessage):
                    ai_message_count += 1
                conversation_length += len(message.content)
            elif isinstance(message, dict):
                role = message.get("role", "user")
                content = message.get("content", "")
                if role == "user":
                    user_message_count += 1
                elif role == "assistant":
                    ai_message_count += 1
                conversation_length += len(content)
            else:
                # Fallback for unknown types
                user_message_count += 1
                conversation_length += len(str(message))

        # Count recent agent responses (last 3 messages)
        recent_messages = messages[-3:] if len(messages) >= 3 else messages
        recent_agent_responses = 0

        for message in recent_messages:
            if isinstance(message, BaseMessage):
                if isinstance(message, AIMessage):
                    recent_agent_responses += 1
            elif isinstance(message, dict):
                if message.get("role") == "assistant":
                    recent_agent_responses += 1

        return {
            "turn_count": len(messages),
            "has_context": len(messages) > 1,
            "recent_agent_responses": recent_agent_responses,
            "user_message_count": user_message_count,
            "conversation_length": conversation_length,
        }

    def get_filtered_conversation_history(
        self, state: UniversalWorkflowState | dict[str, Any], message_manager=None
    ) -> str:
        """
        Get conversation history with existing filtering applied.

        This method integrates with the existing message management system
        to apply any configured filters before formatting.

        Args:
            state: UniversalWorkflowState or dict containing messages
            message_manager: Optional message manager for filtering

        Returns:
            str: Filtered and formatted conversation history
        """
        # Apply existing message filtering if manager provided
        if message_manager:
            filtered_state = message_manager.process_messages(state)
            return self.extract_conversation_history(filtered_state)

        return self.extract_conversation_history(state)


def add_user_message_to_conversation_history(
    state: UniversalWorkflowState | dict[str, Any], message: str
) -> UniversalWorkflowState | dict[str, Any]:
    """
    Add user message to conversation history following SalesGPT human_step pattern.

    This function implements SalesGPT's exact human_step() method pattern:
    "User: " + message + " <END_OF_TURN>"

    Args:
        state: Current workflow state
        message: User message to add

    Returns:
        Updated state with new message

    Example:
        >>> state = UniversalWorkflowState(messages=[])
        >>> updated_state = add_user_message_to_conversation_history(state, "Hello")
        >>> len(updated_state.messages) == 1
        True
    """
    # Defensive programming for state access
    try:
        existing_messages = state.messages
    except AttributeError:
        existing_messages = state.get("messages", [])

    # Create new user message
    user_message = HumanMessage(content=message)

    # Add to existing messages
    updated_messages = list(existing_messages) + [user_message]

    # Return appropriate state type
    if isinstance(state, UniversalWorkflowState):
        return state.copy(update={"messages": updated_messages})
    else:
        # Handle dict state
        updated_state = dict(state)
        updated_state["messages"] = updated_messages
        return updated_state


if __name__ == "__main__":
    """
    Validation function for conversation history manager.

    Tests all functionality with real data to ensure SalesGPT pattern compliance
    and defensive programming robustness.
    """
    import sys

    print("🔍 Validating ConversationHistoryManager...")
    print("=" * 50)

    # Test data
    test_state = UniversalWorkflowState(
        messages=[
            HumanMessage(content="Hello, I need help with my account"),
            AIMessage(
                content="I'd be happy to help you with your account. What specific issue are you experiencing?",
                additional_kwargs={"agent_name": "SupportBot"},
            ),
            HumanMessage(content="I can't log in"),
        ]
    )

    test_dict_state = {
        "messages": [
            HumanMessage(content="Test message"),
            AIMessage(content="Test response"),
        ]
    }

    # Initialize manager
    manager = ConversationHistoryManager(max_history_length=1000)

    # Track validation results
    validation_failures = []
    total_tests = 0

    # Test 1: Basic conversation history extraction
    total_tests += 1
    try:
        history = manager.extract_conversation_history(test_state)
        expected_parts = [
            "User: Hello, I need help with my account <END_OF_TURN>",
            "SupportBot: I'd be happy to help you with your account. What specific issue are you experiencing? <END_OF_TURN>",
            "User: I can't log in <END_OF_TURN>",
        ]

        for part in expected_parts:
            if part not in history:
                validation_failures.append(f"Missing expected part: {part}")

        print("✅ Conversation history extraction test passed")
    except Exception as e:
        validation_failures.append(f"History extraction failed: {str(e)}")

    # Test 2: Dict state handling
    total_tests += 1
    try:
        dict_history = manager.extract_conversation_history(test_dict_state)
        assert "User: Test message <END_OF_TURN>" in dict_history
        assert "Assistant: Test response <END_OF_TURN>" in dict_history
        print("✅ Dict state handling test passed")
    except Exception as e:
        validation_failures.append(f"Dict state handling failed: {str(e)}")

    # Test 3: Empty state handling
    total_tests += 1
    try:
        empty_state = UniversalWorkflowState(messages=[])
        empty_history = manager.extract_conversation_history(empty_state)
        assert empty_history == ""
        print("✅ Empty state handling test passed")
    except Exception as e:
        validation_failures.append(f"Empty state handling failed: {str(e)}")

    # Test 4: Context summary extraction
    total_tests += 1
    try:
        context = manager.get_conversation_context_summary(test_state)
        assert context["turn_count"] == 3
        assert context["has_context"] is True
        assert context["user_message_count"] == 2
        assert context["recent_agent_responses"] == 1
        assert context["conversation_length"] > 0
        print("✅ Context summary extraction test passed")
    except Exception as e:
        validation_failures.append(f"Context summary extraction failed: {str(e)}")

    # Test 5: Message addition function
    total_tests += 1
    try:
        original_state = UniversalWorkflowState(messages=[])
        updated_state = add_user_message_to_conversation_history(
            original_state, "Test message"
        )
        assert len(updated_state.messages) == 1
        assert isinstance(updated_state.messages[0], HumanMessage)
        assert updated_state.messages[0].content == "Test message"
        print("✅ Message addition test passed")
    except Exception as e:
        validation_failures.append(f"Message addition failed: {str(e)}")

    # Test 6: SalesGPT format compliance
    total_tests += 1
    try:
        salesgpt_format = manager.extract_conversation_history(test_state)
        lines = salesgpt_format.split("\n")

        # Verify each line follows SalesGPT format
        for line in lines:
            assert line.endswith(
                "<END_OF_TURN>"
            ), f"Line doesn't end with <END_OF_TURN>: {line}"
            assert line.startswith(
                ("User: ", "SupportBot: ")
            ), f"Line doesn't start with role: {line}"

        print("✅ SalesGPT format compliance test passed")
    except Exception as e:
        validation_failures.append(f"SalesGPT format compliance failed: {str(e)}")

    # Final validation summary
    if validation_failures:
        print(
            f"\n❌ VALIDATION FAILED - {len(validation_failures)} of {total_tests} tests failed:"
        )
        for failure in validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"\n✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("ConversationHistoryManager is ready for production use")
        sys.exit(0)
