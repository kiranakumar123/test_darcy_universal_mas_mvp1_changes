"""
OpenTelemetry OTLP Router for Universal Framework
Tech-agnostic backend routing using industry-standard OpenTelemetry patterns.

Based on research findings: Universal Framework already exceeds industry standards
for LangSmith integration. This module adds the only missing component -
tech-agnostic backend routing via OTLP.

NO CUSTOM BACKEND IMPLEMENTATIONS - uses industry standard OTLP.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Optional OpenTelemetry imports with graceful fallbacks
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    # Fallback for when OpenTelemetry is not available
    trace = None


@dataclass(frozen=True)
class LogEvent:
    """Lightweight log event for OTLP routing."""

    event_id: str
    timestamp: datetime
    component: str
    level: str
    message: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for OTLP export."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "level": self.level,
            "message": self.message,
            "framework": "universal_framework",
            **self.metadata,
        }


class OTLPRouter:
    """
    Standard OpenTelemetry OTLP routing to any backend.
    Follows industry standard patterns - no custom implementations.

    Supports any OTLP-compatible backend:
    - CloudWatch: OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.region.amazonaws.com
    - Datadog: OTEL_EXPORTER_OTLP_ENDPOINT=https://api.datadoghq.com
    - Splunk: OTEL_EXPORTER_OTLP_ENDPOINT=https://ingest.region.signalfx.com
    - Elasticsearch: OTEL_EXPORTER_OTLP_ENDPOINT=https://your-elastic-instance:8200
    """

    def __init__(self):
        from universal_framework.observability import UniversalFrameworkLogger

        self.logger = UniversalFrameworkLogger("otlp_router")
        self.otlp_enabled = False
        self.tracer = None

        if OTEL_AVAILABLE:
            self._setup_otlp_routing()
        else:
            self.logger.warning(
                "OpenTelemetry not available - OTLP routing disabled. "
                "Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp"
            )

    def _setup_otlp_routing(self) -> None:
        """Setup standard OTLP routing to configured backend."""
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")

        if not endpoint:
            self.logger.info("No OTLP endpoint configured - OTLP routing disabled")
            return

        try:
            # Standard OpenTelemetry configuration
            resource = Resource.create(
                {"service.name": "universal-framework", "service.version": "3.1.0"}
            )

            trace.set_tracer_provider(TracerProvider(resource=resource))
            self.tracer = trace.get_tracer(__name__)

            # Standard OTLP exporter (works with any OTLP-compatible backend)
            otlp_exporter = OTLPSpanExporter(
                endpoint=endpoint,
                headers=self._parse_headers(headers) if headers else None,
            )

            span_processor = BatchSpanProcessor(otlp_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)

            self.otlp_enabled = True
            self.logger.info(f"OTLP routing enabled to endpoint: {endpoint}")

        except Exception as e:
            self.logger.error(f"Failed to setup OTLP routing: {e}")
            self.otlp_enabled = False

    def _parse_headers(self, headers_str: str) -> dict[str, str]:
        """Parse OTLP headers from environment variable."""
        headers = {}
        for header in headers_str.split(","):
            if "=" in header:
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()
        return headers

    async def route_log_event(self, event: LogEvent) -> bool:
        """Route log event to OTLP backend if configured."""
        if not self.otlp_enabled or not self.tracer:
            return False

        try:
            # Create OpenTelemetry span for the log event
            with self.tracer.start_as_current_span(
                f"log_{event.level.lower()}"
            ) as span:
                # Add event data as span attributes
                span.set_attribute("log.level", event.level)
                span.set_attribute("log.component", event.component)
                span.set_attribute("log.message", event.message)
                span.set_attribute("log.event_id", event.event_id)

                # Add metadata as span attributes
                for key, value in event.metadata.items():
                    if isinstance(value, str | int | float | bool):
                        span.set_attribute(f"log.{key}", value)

                # Log levels map to span status
                if event.level == "ERROR":
                    span.set_status(trace.Status(trace.StatusCode.ERROR, event.message))
                elif event.level == "WARNING":
                    span.set_status(trace.Status(trace.StatusCode.OK, event.message))
                else:
                    span.set_status(trace.Status(trace.StatusCode.OK))

            return True

        except Exception as e:
            self.logger.error(f"Failed to route log event to OTLP: {e}")
            return False

    def is_enabled(self) -> bool:
        """Check if OTLP routing is enabled."""
        return self.otlp_enabled

    def get_backend_info(self) -> dict[str, Any]:
        """Get information about configured OTLP backend."""
        return {
            "otlp_enabled": self.otlp_enabled,
            "otel_available": OTEL_AVAILABLE,
            "endpoint": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            "service_name": "universal-framework",
        }


# Global OTLP router instance
_otlp_router: OTLPRouter | None = None


def get_otlp_router() -> OTLPRouter:
    """Get the global OTLP router instance."""
    global _otlp_router
    if _otlp_router is None:
        _otlp_router = OTLPRouter()
    return _otlp_router
