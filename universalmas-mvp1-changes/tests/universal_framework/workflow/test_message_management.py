from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from universal_framework.contracts.messages import create_agent_message
from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.workflow.message_management import (
    FullHistoryFilter,
    LastMessageFilter,
    MessageHistoryManager,
    MessageHistoryMode,
    OptimizedSlidingWindowFilter,
    PhaseScopedFilter,
    RoleFilteredFilter,
    SummarizedFilter,
)


def test_summarized_mode_basic_functionality(sample_state_with_messages):
    """Test SUMMARIZED mode creates intelligent summaries."""
    many_messages = sample_state_with_messages.messages * 8
    large_state = sample_state_with_messages.copy(update={"messages": many_messages})

    manager = MessageHistoryManager(
        MessageHistoryMode.SUMMARIZED,
        summary_threshold=20,
        keep_recent=5,
    )
    result = manager.process_messages(large_state)

    assert len(result.messages) == 6
    summary_msg = result.messages[0]
    assert isinstance(summary_msg, AIMessage)
    assert "[CONVERSATION SUMMARY" in summary_msg.content
    assert summary_msg.metadata["type"] == "conversation_summary"
    assert summary_msg.metadata["original_count"] > 0

    recent_messages = result.messages[1:]
    assert len(recent_messages) == 5

    assert "summary_timestamp" in summary_msg.metadata
    assert "workflow_phase" in summary_msg.metadata
    assert "session_id" in summary_msg.metadata


def test_summarized_mode_below_threshold(sample_state_with_messages):
    """Test SUMMARIZED mode preserves all messages below threshold."""
    manager = MessageHistoryManager(
        MessageHistoryMode.SUMMARIZED,
        summary_threshold=50,
        keep_recent=5,
    )
    result = manager.process_messages(sample_state_with_messages)

    assert len(result.messages) == len(sample_state_with_messages.messages)
    assert result.messages == sample_state_with_messages.messages


def test_summarized_mode_integration():
    """Verify SUMMARIZED mode works via MessageHistoryManager."""
    manager_default = MessageHistoryManager(MessageHistoryMode.SUMMARIZED)
    assert isinstance(manager_default.filter, SummarizedFilter)

    manager_configured = MessageHistoryManager(
        MessageHistoryMode.SUMMARIZED,
        summary_threshold=30,
        keep_recent=8,
    )
    assert isinstance(manager_configured.filter, SummarizedFilter)
    assert manager_configured.filter.summary_threshold == 30
    assert manager_configured.filter.keep_recent == 8


def test_summarized_filter_content_quality(sample_state_with_messages):
    """Test summary content includes meaningful conversation information."""
    messages = [
        HumanMessage(
            content="I need help creating a professional email for executives"
        ),
        create_agent_message(
            "email_workflow_orchestrator",
            "batch_requirements_collector",
            "Starting requirements collection",
            WorkflowPhase.BATCH_DISCOVERY,
        ),
        create_agent_message(
            "batch_requirements_collector",
            "email_workflow_orchestrator",
            "Requirements collected successfully",
            WorkflowPhase.BATCH_DISCOVERY,
        ),
        HumanMessage(content="Make it formal and include quarterly results"),
        create_agent_message(
            "email_workflow_orchestrator",
            "strategy_generator",
            "Generating email strategy",
            WorkflowPhase.STRATEGY_ANALYSIS,
        ),
        create_agent_message(
            "strategy_generator",
            "email_workflow_orchestrator",
            "Strategy generation completed",
            WorkflowPhase.STRATEGY_ANALYSIS,
        ),
        HumanMessage(content="The tone should be enthusiastic but professional"),
        AIMessage(
            content="Email generation in progress with professional enthusiastic tone"
        ),
    ]

    mock_state = sample_state_with_messages.copy(
        update={"workflow_phase": WorkflowPhase.STRATEGY_ANALYSIS, "messages": messages}
    )

    filter_instance = SummarizedFilter(summary_threshold=5, keep_recent=2)
    result = filter_instance.filter_messages(messages, mock_state)

    assert len(result) == 3

    summary = result[0]
    assert "User interactions:" in summary.content
    assert "Agent responses:" in summary.content
    assert (
        "email" in summary.content.lower() or "professional" in summary.content.lower()
    )
    assert "Workflow phases:" in summary.content
    assert (
        "batch_discovery" in summary.content.lower()
        or "strategy_analysis" in summary.content.lower()
    )


@pytest.mark.performance
def test_summarized_mode_performance():
    """Test SUMMARIZED mode meets performance requirements."""
    import time

    large_messages = []
    for i in range(1000):
        if i % 3 == 0:
            large_messages.append(
                HumanMessage(content=f"User message {i} with some content")
            )
        elif i % 3 == 1:
            large_messages.append(
                AIMessage(content=f"AI response {i} with detailed content")
            )
        else:
            large_messages.append(
                AIMessage(content=f"Agent action {i} completing task")
            )

    base_state = UniversalWorkflowState(
        session_id="perf_test",
        user_id="perf_user",
        auth_token="perf_token_123456",
    )
    mock_state = base_state.copy(
        update={"workflow_phase": WorkflowPhase.GENERATION, "messages": large_messages}
    )

    filter_instance = SummarizedFilter(summary_threshold=100, keep_recent=10)

    start_time = time.perf_counter()
    result = filter_instance.filter_messages(large_messages, mock_state)
    processing_time = time.perf_counter() - start_time

    assert (
        processing_time < 0.1
    ), f"Processing took {processing_time:.3f}s, must be <100ms"
    assert len(result) == 11

    original_size = len(large_messages)
    filtered_size = len(result)
    reduction_percentage = (original_size - filtered_size) / original_size
    assert (
        reduction_percentage > 0.8
    ), f"Memory reduction {reduction_percentage:.1%} insufficient"


def test_summarized_filter_edge_cases(sample_state_with_messages):
    """Test SummarizedFilter handles edge cases correctly."""
    with pytest.raises(ValueError):
        SummarizedFilter(summary_threshold=5, keep_recent=10)

    with pytest.raises(ValueError):
        SummarizedFilter(summary_threshold=0, keep_recent=5)

    with pytest.raises(ValueError):
        SummarizedFilter(summary_threshold=10, keep_recent=-1)

    filter_instance = SummarizedFilter(summary_threshold=10, keep_recent=3)
    mock_state = sample_state_with_messages

    empty_result = filter_instance.filter_messages([], mock_state)
    assert empty_result == []

    single_message = [HumanMessage(content="Single message")]
    single_result = filter_instance.filter_messages(single_message, mock_state)
    assert single_result == single_message

    threshold_messages = [HumanMessage(content=f"Message {i}") for i in range(10)]
    threshold_result = filter_instance.filter_messages(threshold_messages, mock_state)
    assert threshold_result == threshold_messages


def test_match_case_pattern_coverage():
    """Test that match/case pattern handles all enum values."""
    for mode in MessageHistoryMode:
        manager = MessageHistoryManager(mode)
        assert manager.filter is not None

        if mode == MessageHistoryMode.SUMMARIZED:
            assert isinstance(manager.filter, SummarizedFilter)
        elif mode == MessageHistoryMode.SLIDING_WINDOW:
            assert isinstance(manager.filter, OptimizedSlidingWindowFilter)
        elif mode == MessageHistoryMode.LAST_MESSAGE:
            assert isinstance(manager.filter, LastMessageFilter)
        elif mode == MessageHistoryMode.PHASE_SCOPED:
            assert isinstance(manager.filter, PhaseScopedFilter)
        elif mode == MessageHistoryMode.ROLE_FILTERED:
            assert isinstance(manager.filter, RoleFilteredFilter)
        elif mode == MessageHistoryMode.FULL_HISTORY:
            assert isinstance(manager.filter, FullHistoryFilter)


def test_type_annotation_compliance():
    """Verify all type annotations use modern Python syntax."""
    import inspect

    methods = inspect.getmembers(MessageHistoryManager, predicate=inspect.isfunction)

    for method_name, method in methods:
        signature = inspect.signature(method)
        for param_name, param in signature.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                annotation_str = str(param.annotation)
                assert (
                    "Optional" not in annotation_str
                ), f"Found Optional in {method_name}.{param_name}"
                assert (
                    "Union" not in annotation_str
                ), f"Found Union in {method_name}.{param_name}"


@pytest.mark.performance
def test_optimized_sliding_window_performance():
    """Benchmark optimized sliding window filtering performance."""
    import time

    large_messages = [
        (
            HumanMessage(content=f"User {i}")
            if i % 5 == 0
            else AIMessage(content=f"AI {i}")
        )
        for i in range(1000)
    ]

    state = UniversalWorkflowState(
        session_id="perf",
        user_id="perf",
        auth_token="token123456",
    )

    filter_instance = OptimizedSlidingWindowFilter(window_size=20)

    start = time.perf_counter()
    for _ in range(5):
        filter_instance.filter_messages(large_messages, state)
    end = time.perf_counter()

    avg_ms = (end - start) / 5 * 1000
    assert avg_ms < 10, f"Filtering took {avg_ms:.2f}ms"


def test_optimized_context_preservation():
    """Ensure previous human message is preserved when needed."""
    messages = []
    # Prepend some messages with an older human message
    for i in range(30):
        if i == 0:
            messages.append(HumanMessage(content="start"))
        else:
            messages.append(AIMessage(content=f"AI {i}"))

    state = UniversalWorkflowState(
        session_id="ctx",
        user_id="ctx",
        auth_token="tok",
    )

    filter_instance = OptimizedSlidingWindowFilter(window_size=5)
    result = filter_instance.filter_messages(messages, state)

    assert isinstance(result[0], HumanMessage)
    assert result[0].content == "start"
    assert len(result) == 6


def test_optimized_edge_cases(sample_state_with_messages):
    """Verify optimized filter handles edge scenarios."""
    filter_instance = OptimizedSlidingWindowFilter(window_size=3)

    empty_result = filter_instance.filter_messages([], sample_state_with_messages)
    assert empty_result == []

    small_list = [HumanMessage(content="one"), AIMessage(content="two")]
    assert (
        filter_instance.filter_messages(small_list, sample_state_with_messages)
        == small_list
    )

    no_human = [AIMessage(content=f"AI {i}") for i in range(10)]
    res = filter_instance.filter_messages(no_human, sample_state_with_messages)
    assert res == no_human[-3:]


def test_binary_search_context_preservation():
    """Verify binary search finds most recent HumanMessage correctly."""
    messages = [
        HumanMessage(content="old human 1"),
        AIMessage(content="ai 1"),
        HumanMessage(content="recent human 2"),
        AIMessage(content="ai 2"),
        AIMessage(content="ai 3"),
    ]

    state = UniversalWorkflowState(session_id="bs", user_id="u", auth_token="t")
    filter_instance = OptimizedSlidingWindowFilter(window_size=2)
    result = filter_instance.filter_messages(messages, state)

    assert len(result) == 3
    assert isinstance(result[0], HumanMessage)
    assert result[0].content == "recent human 2"
    assert result[1].content == "ai 2"
    assert result[2].content == "ai 3"
