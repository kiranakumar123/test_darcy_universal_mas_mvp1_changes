from unittest.mock import MagicMock

from universal_framework.observability.trace_correlation import (
    CrossPlatformTraceCorrelator,
)


class DummySpanContext:
    trace_id = 0x1
    span_id = 0x2
    trace_flags = 1


class DummySpan:
    def is_recording(self) -> bool:
        return True

    def get_span_context(self):
        return DummySpanContext()


def test_get_current_trace_context(monkeypatch):
    monkeypatch.setattr(
        "universal_framework.observability.trace_correlation.otel_trace.get_current_span",
        lambda: DummySpan(),
    )
    mock_pii = MagicMock()
    mock_pii.hash_session_id.return_value = "hashed"
    corr = CrossPlatformTraceCorrelator(mock_pii)
    ctx = corr.get_current_trace_context("session")
    assert ctx["session_hash"] == "hashed"
    assert ctx["opentelemetry"]["trace_id"] == "00000000000000000000000000000001"


def test_add_correlation_to_langsmith_trace(monkeypatch):
    dummy_client = MagicMock()
    monkeypatch.setattr(
        "universal_framework.observability.trace_correlation.Client",
        lambda: dummy_client,
    )
    mock_pii = MagicMock()
    mock_pii.hash_session_id.return_value = "hashed"
    corr = CrossPlatformTraceCorrelator(mock_pii)
    ctx = {"session_hash": "hashed", "opentelemetry": {"trace_id": "1", "span_id": "2"}}
    corr.add_correlation_to_langsmith_trace("trace", ctx)
    dummy_client.update_run.assert_called_once()
