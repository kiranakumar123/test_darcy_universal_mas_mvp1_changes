"""Correlate OpenTelemetry and LangSmith traces using shared session context."""

from __future__ import annotations

import time
from typing import Any

from langsmith import Client

# Make OpenTelemetry import optional and gated by feature flags
try:
    from universal_framework.config.feature_flags import feature_flags

    if feature_flags.is_enabled("LANGSMITH_TRACING"):
        from opentelemetry import trace as otel_trace

        _opentelemetry_available = True
    else:
        _opentelemetry_available = False
        otel_trace = None  # type: ignore
except ImportError:
    _opentelemetry_available = False
    otel_trace = None  # type: ignore

from universal_framework.compliance.pii_detector import PIIDetector
from universal_framework.observability.logging_contracts import LoggingFactory

logger = LoggingFactory.create_observability_logger("trace_correlation")


class CrossPlatformTraceCorrelator:
    """Correlate OpenTelemetry and LangSmith traces."""

    def __init__(self, pii_detector: PIIDetector) -> None:
        self.pii_detector = pii_detector
        # Only initialize OpenTelemetry tracer if available and enabled
        if _opentelemetry_available and otel_trace:
            self.otel_tracer = otel_trace.get_tracer(__name__)
        else:
            self.otel_tracer = None
        try:
            self.langsmith_client = Client()
        except Exception as exc:  # noqa: BLE001
            logger.log_error(
                error_type="langsmith_client_unavailable",
                error_message=str(exc),
            )
            self.langsmith_client = None

    def get_current_trace_context(self, session_id: str) -> dict[str, Any]:
        """Get correlation context using OpenTelemetry."""
        session_hash = self.pii_detector.hash_session_id(session_id)
        otel_context: dict[str, Any] = {}

        # Only get OpenTelemetry context if available and enabled
        if _opentelemetry_available and otel_trace:
            current_span = otel_trace.get_current_span()
            if current_span and current_span.is_recording():
                sc = current_span.get_span_context()
                otel_context = {
                    "trace_id": f"{sc.trace_id:032x}",
                    "span_id": f"{sc.span_id:016x}",
                    "trace_flags": sc.trace_flags,
                }
        return {
            "session_hash": session_hash,
            "opentelemetry": otel_context,
            "correlation_timestamp": time.time(),
        }

    def add_correlation_to_langsmith_trace(
        self, trace_id: str, correlation_context: dict[str, Any]
    ) -> None:
        """Add OpenTelemetry correlation data to a LangSmith trace."""
        if not self.langsmith_client:
            return
        try:
            correlation_metadata = {
                "otel_trace_id": correlation_context.get("opentelemetry", {}).get(
                    "trace_id"
                ),
                "otel_span_id": correlation_context.get("opentelemetry", {}).get(
                    "span_id"
                ),
                "session_hash": correlation_context.get("session_hash"),
                "cross_platform_correlation": True,
            }
            self.langsmith_client.update_run(
                trace_id,
                extra={"correlation": correlation_metadata},
            )
        except Exception as exc:  # noqa: BLE001
            logger.log_error(
                error_type="correlation_metadata_failed",
                error_message=str(exc),
            )
