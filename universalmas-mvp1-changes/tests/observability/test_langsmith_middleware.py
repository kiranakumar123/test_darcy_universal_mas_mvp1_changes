from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from universal_framework.observability.langsmith_middleware import (
    LangSmithAPITracingMiddleware,
)


class DummyTrace:
    def __init__(self, **kwargs):
        self.metadata = kwargs.get("metadata", {})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_middleware_traces_and_hashes(monkeypatch):
    app = FastAPI()

    mock_pii = MagicMock()
    mock_pii.hash_session_id.return_value = "hashed_session"
    mock_pii.redact_metadata.return_value = {}

    cb = MagicMock()
    cb.__aenter__ = AsyncMock(return_value=None)
    cb.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr(
        "universal_framework.observability.langsmith_middleware.trace",
        lambda **_: DummyTrace(),
    )

    counter = MagicMock()
    counter.labels.return_value.inc = MagicMock()
    monkeypatch.setattr(
        "universal_framework.observability.langsmith_middleware.real_agent_executions",
        counter,
    )
    monkeypatch.setattr(
        "universal_framework.observability.langsmith_middleware.langsmith_api_traces",
        counter,
    )
    monkeypatch.setattr(
        "universal_framework.observability.langsmith_middleware.trace_correlation_success",
        counter,
    )

    class DummyCorrelator:
        def __init__(self, detector):
            self.detector = detector

        def get_current_trace_context(self, session_id: str):
            return {
                "session_hash": self.detector.hash_session_id(session_id),
                "opentelemetry": {},
                "correlation_timestamp": 0,
            }

        def add_correlation_to_langsmith_trace(self, trace_id: str, ctx: dict):
            return None

    monkeypatch.setattr(
        "universal_framework.observability.langsmith_middleware.CrossPlatformTraceCorrelator",
        lambda pii: DummyCorrelator(pii),
    )

    app.add_middleware(
        LangSmithAPITracingMiddleware,
        pii_detector=mock_pii,
        circuit_breaker=cb,
    )

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    client = TestClient(app)
    resp = client.get("/ping", headers={"X-Session-ID": "abc"})
    assert resp.status_code == 200
    assert resp.headers["X-LangSmith-Session"] == "hashed_session"
    assert mock_pii.hash_session_id.call_count == 2
    assert cb.__aenter__.called
    assert counter.labels.called


def test_trace_correlation_integration_working(monkeypatch):
    """Test actual working trace correlation between OpenTelemetry and LangSmith."""
    app = FastAPI()

    mock_pii = MagicMock()
    mock_pii.hash_session_id.return_value = "hashed_session"
    mock_pii.redact_metadata.return_value = {"endpoint": "/test"}

    cb = MagicMock()
    cb.__aenter__ = AsyncMock(return_value=None)
    cb.__aexit__ = AsyncMock(return_value=None)

    mock_otel_context = {
        "session_hash": "hashed_session",
        "opentelemetry": {
            "trace_id": "00000000000000000000000000000001",
            "span_id": "0000000000000002",
        },
        "correlation_timestamp": 1234567890,
    }

    mock_correlator = MagicMock()
    mock_correlator.get_current_trace_context.return_value = mock_otel_context
    mock_correlator.add_correlation_to_langsmith_trace = MagicMock()

    class CorrelatedTrace:
        def __init__(self, **kwargs):
            self.metadata = kwargs.get("metadata", {})
            self.id = "langsmith_trace_123"
            assert "otel_correlation" in self.metadata
            assert "cross_platform_correlated" in self.metadata

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "universal_framework.observability.langsmith_middleware.trace",
        lambda **kwargs: CorrelatedTrace(**kwargs),
    )

    monkeypatch.setattr(
        "universal_framework.observability.langsmith_middleware.CrossPlatformTraceCorrelator",
        lambda pii_detector: mock_correlator,
    )

    counter = MagicMock()
    counter.labels.return_value.inc = MagicMock()
    monkeypatch.setattr(
        "universal_framework.observability.langsmith_middleware.real_agent_executions",
        counter,
    )
    monkeypatch.setattr(
        "universal_framework.observability.langsmith_middleware.langsmith_api_traces",
        counter,
    )

    app.add_middleware(
        LangSmithAPITracingMiddleware,
        pii_detector=mock_pii,
        circuit_breaker=cb,
    )

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)
    resp = client.get("/test", headers={"X-Session-ID": "test_session"})

    assert resp.status_code == 200
    assert resp.headers["X-LangSmith-Session"] == "hashed_session"

    mock_correlator.get_current_trace_context.assert_called_once_with("test_session")
    mock_correlator.add_correlation_to_langsmith_trace.assert_called_once_with(
        "langsmith_trace_123", mock_otel_context
    )
