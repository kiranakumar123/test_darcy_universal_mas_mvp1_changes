import asyncio
from types import SimpleNamespace

import pytest

from universal_framework.compliance import PIIDetector, RedactionConfig
from universal_framework.config.environment import get_langsmith_config
from universal_framework.observability.enterprise_langsmith import (
    EnterpriseLangSmithConfig,
    LangSmithCircuitBreaker,
    ToolCallTracer,
    enhance_trace_real_agent_execution,
)


def test_tool_call_tracer_redacts_pii(tmp_path, monkeypatch):
    detector = PIIDetector(RedactionConfig())
    config = EnterpriseLangSmithConfig(pii_detector=detector)
    tracer = ToolCallTracer(config)

    call = SimpleNamespace(
        type="api",
        function=SimpleNamespace(name="send_email", arguments="to user@example.com"),
    )
    metadata = tracer.create_tool_call_metadata([call], {}, "session1")
    assert metadata["pending_tool_calls"] == 1
    preview = metadata["tool_calls_detail"][0]["arguments_preview"]
    assert "[EMAIL_REDACTED]" in preview
    assert metadata["session_hash"].startswith("session_hash_")


def test_get_langsmith_config_from_toml(tmp_path, monkeypatch):
    content = """
[langsmith.enterprise]
api_key = "toml-key"
[langsmith.environments.development]
sampling_rate = 0.5
"""
    cfg = tmp_path / "langsmith.toml"
    cfg.write_text(content)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    config = get_langsmith_config()
    assert config["api_key"] == "toml-key"
    assert config["sampling_rate"] == 0.5


@pytest.mark.asyncio
async def test_circuit_breaker_transitions() -> None:
    cb = LangSmithCircuitBreaker(
        {"failure_threshold": 1, "recovery_timeout_seconds": 0.1}
    )

    # First failure opens the circuit
    with pytest.raises(ValueError):
        async with cb:
            raise ValueError()
    assert cb.state == "OPEN"

    # Wait for half-open transition
    await asyncio.sleep(0.11)
    async with cb:
        pass
    assert cb.state == "CLOSED"


@pytest.mark.asyncio
async def test_enhanced_tracing_fallback(monkeypatch) -> None:
    """Decorator falls back when no enterprise config provided."""

    # patch langsmith.traceable to prevent network calls
    monkeypatch.setattr("langsmith.traceable", lambda **_: (lambda f: f))

    @enhance_trace_real_agent_execution("agent", "session")
    async def dummy() -> str:
        return "ok"

    result = await dummy()
    assert result == "ok"
