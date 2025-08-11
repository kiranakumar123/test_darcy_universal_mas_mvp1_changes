"""Simple metrics collection without external dependencies."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MetricEvent:
    """Single metric event record."""

    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class SimpleMetricsCollector:
    """Lightweight metrics collector without external dependencies."""

    def __init__(self, max_events: int = 10000) -> None:
        self.max_events = max_events
        self.events: deque[MetricEvent] = deque(maxlen=max_events)
        self.counters: dict[str, int] = defaultdict(int)
        self.histograms: dict[str, list[float]] = defaultdict(list)
        self.gauges: dict[str, float] = {}
        self._lock = threading.Lock()

    def increment_counter(
        self, name: str, labels: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric."""
        with self._lock:
            key = self._make_key(name, labels or {})
            self.counters[key] += 1
            self.events.append(MetricEvent(name, 1.0, labels or {}))

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record a histogram observation."""
        with self._lock:
            key = self._make_key(name, labels or {})
            self.histograms[key].append(value)
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-500:]
            self.events.append(MetricEvent(name, value, labels or {}))

    def set_gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Set a gauge metric value."""
        with self._lock:
            key = self._make_key(name, labels or {})
            self.gauges[key] = value
            self.events.append(MetricEvent(name, value, labels or {}))

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> int:
        """Get current counter value."""
        key = self._make_key(name, labels or {})
        return self.counters.get(key, 0)

    def get_histogram_stats(
        self, name: str, labels: dict[str, str] | None = None
    ) -> dict[str, float]:
        """Get histogram statistics."""
        key = self._make_key(name, labels or {})
        values = self.histograms.get(key, [])
        if not values:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
        return {
            "count": len(values),
            "sum": float(sum(values)),
            "avg": float(sum(values)) / len(values),
            "min": float(min(values)),
            "max": float(max(values)),
        }

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all current metrics."""
        with self._lock:
            return {
                "counters": dict(self.counters),
                "histograms": {k: self.get_histogram_stats(k) for k in self.histograms},
                "gauges": dict(self.gauges),
                "total_events": len(self.events),
            }

    def _make_key(self, name: str, labels: dict[str, str]) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


_metrics_collector = SimpleMetricsCollector()


@contextmanager
def measure_agent_execution(agent_name: str, is_real_agent: bool = True):
    """Context manager for measuring agent execution time."""
    start_time = time.time()
    labels = {
        "agent_name": agent_name,
        "agent_type": "real" if is_real_agent else "simulation",
    }
    try:
        yield
    except Exception:
        _metrics_collector.increment_counter("agent_execution_failures_total", labels)
        raise
    finally:
        duration = time.time() - start_time
        _metrics_collector.observe_histogram(
            "agent_execution_duration_seconds", duration, labels
        )
        _metrics_collector.increment_counter("agent_executions_total", labels)


@contextmanager
def measure_routing_operation(from_node: str, to_node: str, decision_type: str):
    """Context manager for measuring routing operations."""
    start_time = time.time()
    labels = {
        "from_node": from_node,
        "to_node": to_node,
        "decision_type": decision_type,
    }
    try:
        yield
    finally:
        duration = time.time() - start_time
        _metrics_collector.observe_histogram(
            "routing_duration_seconds", duration, labels
        )
        _metrics_collector.increment_counter("routing_decisions_total", labels)


def get_metrics_summary() -> dict[str, Any]:
    """Get summary of all metrics."""
    return _metrics_collector.get_all_metrics()


def record_workflow_phase_transition(from_phase: str, to_phase: str) -> None:
    """Record workflow phase transition."""
    labels = {"from_phase": from_phase, "to_phase": to_phase}
    _metrics_collector.increment_counter("workflow_phase_transitions_total", labels)


def record_error_recovery(
    failed_node: str, recovery_type: str, retry_count: int
) -> None:
    """Record error recovery event."""
    labels = {
        "failed_node": failed_node,
        "recovery_type": recovery_type,
        "retry_count": str(retry_count),
    }
    _metrics_collector.increment_counter("error_recovery_events_total", labels)
