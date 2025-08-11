"""Message history management utilities for workflows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from universal_framework.contracts.messages import AgentMessage
from universal_framework.contracts.redis.interfaces import (
    RedisSessionManagerInterface,
)
from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.redis.session_storage import SessionStorage
from universal_framework.workflow.orchestrator import (
    create_email_workflow_orchestrator,
)


class MessageHistoryMode(Enum):
    """Supported message history strategies."""

    FULL_HISTORY = "full_history"
    LAST_MESSAGE = "last_message"
    PHASE_SCOPED = "phase_scoped"
    SLIDING_WINDOW = "sliding_window"
    ROLE_FILTERED = "role_filtered"
    SUMMARIZED = "summarized"


class MessageFilter(Protocol):
    """Protocol for message filtering strategies."""

    def filter_messages(
        self, messages: list[BaseMessage], state: UniversalWorkflowState
    ) -> list[BaseMessage]: ...


class FullHistoryFilter:
    """Return all messages without filtering."""

    def filter_messages(
        self, messages: list[BaseMessage], state: UniversalWorkflowState
    ) -> list[BaseMessage]:
        return messages


class LastMessageFilter:
    """Return only the most recent message."""

    def filter_messages(
        self, messages: list[BaseMessage], state: UniversalWorkflowState
    ) -> list[BaseMessage]:
        return messages[-1:] if messages else []


class PhaseScopedFilter:
    """Return messages belonging to the current workflow phase."""

    def filter_messages(
        self, messages: list[BaseMessage], state: UniversalWorkflowState
    ) -> list[BaseMessage]:
        # Defensive programming for workflow_phase access
        try:
            current_phase = state.workflow_phase
        except AttributeError:
            current_phase = WorkflowPhase(
                state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
            )

        return [
            m
            for m in messages
            if isinstance(m, AgentMessage) and m.phase == current_phase
        ]


class OptimizedSlidingWindowFilter:
    """Performance-optimized sliding window with Redis integration hooks."""

    def __init__(self, window_size: int = 10, redis_coordinator: Any = None) -> None:
        """Initialize optimized sliding window filter."""
        if window_size <= 0:
            raise ValueError("window_size must be positive")

        self.window_size = window_size
        self.redis_coordinator = redis_coordinator

        self._small_window_threshold = min(5, window_size)
        self._context_search_limit = max(20, window_size * 2)

    def filter_messages(
        self,
        messages: list[BaseMessage],
        state: UniversalWorkflowState,
    ) -> list[BaseMessage]:
        """Filter messages using optimized sliding window algorithm."""
        if len(messages) <= self.window_size:
            return messages

        start_index = len(messages) - self.window_size
        recent_messages = messages[start_index:]

        if not self._has_human_message(recent_messages) and start_index > 0:
            context_message = self._find_recent_human_context(messages, start_index)
            if context_message:
                recent_messages.insert(0, context_message)

        coordination = self._coordinate_with_redis(state)
        return self._apply_distributed_optimizations(recent_messages, coordination)

    def _has_human_message(self, messages: list[BaseMessage]) -> bool:
        check_count = min(self._small_window_threshold, len(messages))
        for i in range(len(messages) - 1, len(messages) - check_count - 1, -1):
            if isinstance(messages[i], HumanMessage):
                return True
        return False

    def _find_recent_human_context(
        self, messages: list[BaseMessage], before_index: int
    ) -> BaseMessage | None:
        """Binary search for most recent HumanMessage before index."""
        search_start = max(0, before_index - self._context_search_limit)
        search_end = before_index - 1

        left, right = search_start, search_end
        result_index = -1
        while left <= right:
            mid = (left + right) // 2
            if isinstance(messages[mid], HumanMessage):
                result_index = mid
                left = mid + 1
            else:
                right = mid - 1

        return messages[result_index] if result_index != -1 else None

    def _coordinate_with_redis(
        self, state: UniversalWorkflowState
    ) -> dict[str, Any] | None:
        if not self.redis_coordinator:
            return None
        try:
            coordination_data = {
                "window_size": self.window_size,
                "message_count": len(state.messages),
                "timestamp": datetime.now().isoformat(),
            }
            # Placeholder for future Redis coordination implementation
            # self.redis_coordinator.set_filter_coordination(session_key, coordination_data)
            return coordination_data
        except Exception:  # noqa: BLE001
            return None

    def _apply_distributed_optimizations(
        self,
        messages: list[BaseMessage],
        coordination_data: dict[str, Any] | None,
    ) -> list[BaseMessage]:
        if not coordination_data:
            return messages
        # Placeholder for distributed optimization logic
        return messages

    def get_performance_metrics(self) -> dict[str, Any]:
        return {
            "window_size": self.window_size,
            "algorithm": "optimized_sliding_window",
            "context_search_limit": self._context_search_limit,
            "redis_enabled": self.redis_coordinator is not None,
            "performance_target": "<10ms for 1000+ messages",
        }


class RoleFilteredFilter:
    """Return messages from specific roles."""

    def __init__(self, included_roles: list[str] | None = None) -> None:
        self.included_roles = included_roles or ["human", "assistant", "agent"]

    def filter_messages(
        self, messages: list[BaseMessage], state: UniversalWorkflowState
    ) -> list[BaseMessage]:
        def _role(msg: BaseMessage) -> str:
            if isinstance(msg, HumanMessage):
                return "human"
            if isinstance(msg, AIMessage):
                return "assistant"
            if isinstance(msg, AgentMessage):
                return "agent"
            return "other"

        return [m for m in messages if _role(m) in self.included_roles]


class SummarizedFilter:
    """Summarize old messages to reduce memory usage while preserving conversation context."""

    def __init__(self, summary_threshold: int = 20, keep_recent: int = 5) -> None:
        """Initialize conversation summarization filter."""
        if summary_threshold < keep_recent:
            raise ValueError("summary_threshold must be >= keep_recent")
        if summary_threshold <= 0 or keep_recent < 0:
            raise ValueError("Threshold and keep_recent must be positive")

        self.summary_threshold = summary_threshold
        self.keep_recent = keep_recent

    def filter_messages(
        self, messages: list[BaseMessage], state: UniversalWorkflowState
    ) -> list[BaseMessage]:
        """Filter messages using intelligent conversation summarization."""
        if len(messages) <= self.summary_threshold:
            return messages

        messages_to_summarize = (
            messages[: -self.keep_recent] if self.keep_recent > 0 else messages
        )
        recent_messages = messages[-self.keep_recent :] if self.keep_recent > 0 else []

        summary_content = self._create_conversation_summary(
            messages_to_summarize, state
        )

        summary_message: BaseMessage = AIMessage(
            content=f"[CONVERSATION SUMMARY: {len(messages_to_summarize)} messages] {summary_content}",
            metadata={
                "type": "conversation_summary",
                "original_count": len(messages_to_summarize),
                "summary_timestamp": datetime.now().isoformat(),
                "summary_strategy": "intelligent_threshold",
                "workflow_phase": (
                    state.workflow_phase.value
                    if hasattr(state, "workflow_phase")
                    else state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value)
                ),
                "session_id": getattr(state, "session_id", "unknown"),
            },
        )

        return [summary_message] + recent_messages

    def _create_conversation_summary(
        self, messages: list[BaseMessage], state: UniversalWorkflowState
    ) -> str:
        """Create intelligent summary of conversation segment."""
        if not messages:
            return "Empty conversation segment"

        human_messages = [
            msg.content for msg in messages if isinstance(msg, HumanMessage)
        ]

        agent_messages: list[str] = []
        for msg in messages:
            if hasattr(msg, "agent_name"):
                agent_name = getattr(msg, "agent_name", "Agent")
                content_str = msg.content
                content_preview = (
                    content_str[:100] + "..." if len(content_str) > 100 else content_str
                )
                agent_messages.append(f"{agent_name}: {content_preview}")
            elif isinstance(msg, AIMessage):
                content_str = msg.content
                content_preview = (
                    content_str[:100] + "..." if len(content_str) > 100 else content_str
                )
                agent_messages.append(f"Assistant: {content_preview}")

        workflow_phases = self._extract_workflow_phases(messages)
        key_themes = self._extract_conversation_themes(human_messages)

        summary_parts: list[str] = []

        if human_messages:
            summary_parts.append(f"User interactions: {len(human_messages)}")
            if key_themes:
                summary_parts.append(f"Key topics: {', '.join(key_themes[:3])}")
            if len(human_messages) >= 2:
                first_input = (
                    human_messages[0][:80] + "..."
                    if len(human_messages[0]) > 80
                    else human_messages[0]
                )
                last_input = (
                    human_messages[-1][:80] + "..."
                    if len(human_messages[-1]) > 80
                    else human_messages[-1]
                )
                summary_parts.append(f"Initial request: '{first_input}'")
                summary_parts.append(f"Latest input: '{last_input}'")
            elif len(human_messages) == 1:
                single_input = (
                    human_messages[0][:120] + "..."
                    if len(human_messages[0]) > 120
                    else human_messages[0]
                )
                summary_parts.append(f"User request: '{single_input}'")

        if agent_messages:
            summary_parts.append(f"Agent responses: {len(agent_messages)}")

        if workflow_phases:
            summary_parts.append(f"Workflow phases: {' → '.join(workflow_phases)}")

        summary_parts.append(f"Message span: {len(messages)} messages")

        return ". ".join(summary_parts)

    def _extract_workflow_phases(self, messages: list[BaseMessage]) -> list[str]:
        """Extract unique workflow phases from message sequence."""
        phases: list[str] = []
        for msg in messages:
            if hasattr(msg, "phase"):
                phase_value = (
                    msg.phase.value if hasattr(msg.phase, "value") else str(msg.phase)
                )
                if phase_value not in phases:
                    phases.append(phase_value)
        return phases

    def _extract_conversation_themes(self, human_messages: list[str]) -> list[str]:
        """Extract key themes from user messages using simple keyword analysis."""
        if not human_messages:
            return []

        theme_keywords: dict[str, list[str]] = {
            "email": ["email", "message", "communication", "send", "compose"],
            "strategy": ["strategy", "plan", "approach", "method", "way"],
            "requirements": ["need", "require", "want", "should", "must"],
            "analysis": ["analyze", "review", "check", "examine", "study"],
            "generation": ["create", "generate", "make", "build", "produce"],
            "professional": [
                "professional",
                "business",
                "formal",
                "corporate",
            ],
            "urgent": ["urgent", "asap", "immediately", "quickly", "fast"],
        }

        themes: list[str] = []
        combined_text = " ".join(human_messages).lower()

        for theme, keywords in theme_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                themes.append(theme)

        return themes[:5]


class MessageHistoryManager:
    """Manage message history based on filtering strategy."""

    def __init__(
        self,
        mode: MessageHistoryMode = MessageHistoryMode.FULL_HISTORY,
        custom_filter: MessageFilter | None = None,
        **filter_kwargs: Any,
    ) -> None:
        self.mode = mode
        self.filter = self._create_filter(mode, custom_filter, **filter_kwargs)

    def _create_filter(
        self,
        mode: MessageHistoryMode,
        custom_filter: MessageFilter | None,
        **kwargs: Any,
    ) -> MessageFilter:
        """Create appropriate filter based on mode using modern Python patterns."""
        if custom_filter:
            return custom_filter

        match mode:
            case MessageHistoryMode.FULL_HISTORY:
                return FullHistoryFilter()
            case MessageHistoryMode.LAST_MESSAGE:
                return LastMessageFilter()
            case MessageHistoryMode.PHASE_SCOPED:
                return PhaseScopedFilter()
            case MessageHistoryMode.SLIDING_WINDOW:
                window_size = kwargs.get("window_size", 10)
                redis_coordinator = kwargs.get("redis_coordinator")
                return OptimizedSlidingWindowFilter(window_size, redis_coordinator)
            case MessageHistoryMode.ROLE_FILTERED:
                included_roles = kwargs.get(
                    "included_roles", ["human", "assistant", "agent"]
                )
                return RoleFilteredFilter(included_roles)
            case MessageHistoryMode.SUMMARIZED:
                summary_threshold = kwargs.get("summary_threshold", 20)
                keep_recent = kwargs.get("keep_recent", 5)
                return SummarizedFilter(summary_threshold, keep_recent)
            case _:
                return FullHistoryFilter()

    def process_messages(self, state: UniversalWorkflowState) -> UniversalWorkflowState:
        """Return new state with filtered messages."""
        filtered = self.filter.filter_messages(state.messages, state)
        return state.copy(update={"messages": filtered})


def create_message_aware_workflow_orchestrator(
    available_agents: list[str],
    redis_session_manager: RedisSessionManagerInterface | None = None,
    message_history_mode: MessageHistoryMode = MessageHistoryMode.FULL_HISTORY,
    session_storage: SessionStorage | None = None,
    **message_history_kwargs: Any,
) -> Callable[[UniversalWorkflowState], Awaitable[UniversalWorkflowState]]:
    """Wrap workflow orchestrator with message history management."""

    history_manager = MessageHistoryManager(
        message_history_mode, **message_history_kwargs
    )
    base_orchestrator = create_email_workflow_orchestrator(
        available_agents, session_storage=session_storage
    )

    async def message_orchestrator(
        state: UniversalWorkflowState,
    ) -> UniversalWorkflowState:
        filtered_state = history_manager.process_messages(state)
        return await base_orchestrator(filtered_state)

    return message_orchestrator


def benchmark_sliding_window_performance(
    message_counts: list[int] | None = None,
) -> dict[str, float]:
    """Benchmark optimized sliding window performance across message volumes."""
    import time

    if message_counts is None:
        message_counts = [10, 50, 100, 500, 1000]

    results: dict[str, float] = {}
    filter_instance = OptimizedSlidingWindowFilter(window_size=20)

    for count in message_counts:
        test_messages = [
            (
                HumanMessage(content=f"Message {i}")
                if i % 5 == 0
                else AIMessage(content=f"Response {i}")
            )
            for i in range(count)
        ]
        mock_state = UniversalWorkflowState(
            session_id="benchmark",
            user_id="test",
            auth_token="benchmark_token",
        )

        start = time.perf_counter()
        for _ in range(10):
            filter_instance.filter_messages(test_messages, mock_state)
        end = time.perf_counter()
        results[f"{count}_messages"] = (end - start) / 10 * 1000

    return results


def validate_optimization_correctness(
    original_filter: Any,
    optimized_filter: OptimizedSlidingWindowFilter,
    test_scenarios: list[list[BaseMessage]] | None = None,
) -> bool:
    """Validate that optimized filter produces identical results to original."""

    if test_scenarios is None:
        test_scenarios = [
            [],
            [HumanMessage(content="Single message")],
            [HumanMessage(content=f"Message {i}") for i in range(5)],
            [AIMessage(content=f"Response {i}") for i in range(20)],
            [
                (
                    HumanMessage(content="Human")
                    if i % 3 == 0
                    else AIMessage(content=f"AI {i}")
                )
                for i in range(100)
            ],
        ]

    mock_state = UniversalWorkflowState(
        session_id="validation",
        user_id="test",
        auth_token="validation_token",
    )

    for scenario in test_scenarios:
        original_result = original_filter.filter_messages(scenario, mock_state)
        optimized_result = optimized_filter.filter_messages(scenario, mock_state)

        if len(original_result) != len(optimized_result):
            return False
        for orig, opt in zip(original_result, optimized_result, strict=False):
            if orig.content != opt.content or type(orig) is not type(opt):
                return False

    return True
