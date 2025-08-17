"""Enhanced performance monitoring for real vs simulated agents using DataDog."""

from __future__ import annotations

from ..core.logging_foundation import get_safe_logger

logger = get_safe_logger(__name__)


class DataDogMetrics:
    """DataDog metrics client for enterprise monitoring."""

    def __init__(self):
        """Initialize DataDog metrics client."""
        # Import feature flags to check safe mode
        from ..config.feature_flags import feature_flags

        self.enabled = False
        self.statsd = None

        # Only enable DataDog if safe mode allows and compliance monitoring is enabled
        if not feature_flags.is_safe_mode() and feature_flags.is_enabled(
            "COMPLIANCE_MONITORING"
        ):
            try:
                import datadog

                # DataDog will be configured via environment variables
                # DD_API_KEY, DD_APP_KEY, DD_SITE, etc.
                self.statsd = datadog.statsd
                self.enabled = True
                logger.info("DataDog metrics enabled")
            except ImportError:
                logger.warning("DataDog not available, metrics disabled")
                self.enabled = False
                self.statsd = None
        else:
            logger.info("DataDog metrics disabled in safe mode")

    def increment(
        self, metric: str, value: int = 1, tags: list[str] | None = None
    ) -> None:
        """Increment a counter metric."""
        if self.enabled and self.statsd:
            self.statsd.increment(metric, value=value, tags=tags or [])

    def histogram(
        self, metric: str, value: float, tags: list[str] | None = None
    ) -> None:
        """Record a histogram metric."""
        if self.enabled and self.statsd:
            self.statsd.histogram(metric, value=value, tags=tags or [])

    def gauge(self, metric: str, value: float, tags: list[str] | None = None) -> None:
        """Set a gauge metric."""
        if self.enabled and self.statsd:
            self.statsd.gauge(metric, value=value, tags=tags or [])


# Global metrics instance
metrics = DataDogMetrics()


def record_real_agent_execution(
    agent_type: str, node_name: str, duration: float, success: bool
) -> None:
    """Record real agent execution metrics."""
    status = "success" if success else "failure"
    metrics.increment(
        "universal_framework.real_agent_executions",
        tags=[f"agent_type:{agent_type}", f"node_name:{node_name}", f"status:{status}"],
    )
    if success:
        metrics.histogram(
            "universal_framework.agent_execution_duration",
            duration,
            tags=[f"agent_type:{agent_type}", f"node_name:{node_name}"],
        )


def update_circuit_breaker_status(agent_type: str, status_code: int) -> None:
    """Update circuit breaker status metric."""
    # 0=healthy, 1=degraded, 2=failed
    metrics.gauge(
        "universal_framework.circuit_breaker_status",
        float(status_code),
        tags=[f"agent_type:{agent_type}"],
    )


def record_langsmith_trace(
    endpoint: str, status: str, correlation_success: bool
) -> None:
    """Record LangSmith API trace metrics."""
    metrics.increment(
        "universal_framework.langsmith_api_traces",
        tags=[
            f"endpoint:{endpoint}",
            f"status:{status}",
            f"correlation_success:{correlation_success}",
        ],
    )


def record_trace_correlation_success(platform: str) -> None:
    """Record successful trace correlation."""
    metrics.increment(
        "universal_framework.trace_correlation_success", tags=[f"platform:{platform}"]
    )
