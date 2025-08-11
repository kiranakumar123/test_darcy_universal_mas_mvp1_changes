"""Enhanced performance monitoring for real vs simulated agents using DataDog."""

from __future__ import annotations

from ..core.logging_foundation import get_safe_logger

logger = get_safe_logger(__name__)


class DataDogMetrics:
    """DataDog metrics client for enterprise monitoring."""

    def __init__(self):
        """Initialize DataDog metrics client."""
        self.enabled = False
        self.statsd = None

        # Import feature flags to check safe mode
        from ..config.feature_flags import feature_flags

        # Only enable DataDog if safe mode allows and properly configured
        if not feature_flags.is_safe_mode() and feature_flags.is_enabled(
            "COMPLIANCE_MONITORING"
        ):
            import os

            if os.getenv("DD_API_KEY") or os.getenv("DATADOG_API_KEY"):
                try:
                    import datadog

                    # DataDog will be configured via environment variables
                    # DD_API_KEY, DD_APP_KEY, DD_SITE, etc.
                    self.statsd = datadog.statsd
                    self.enabled = True
                    logger.info("DataDog metrics enabled")
                except ImportError:
                    logger.info("DataDog not available, metrics disabled")
            else:
                logger.debug("DataDog API key not configured, metrics disabled")
        else:
            logger.debug("DataDog metrics disabled in safe mode")

    def increment(
        self, metric: str, value: int = 1, tags: list[str] | None = None
    ) -> None:
        """Increment a counter metric."""
        if self.enabled and self.statsd:
            try:
                self.statsd.increment(metric, value=value, tags=tags or [])
            except Exception as e:
                logger.debug("DataDog metric failed", error=str(e), metric=metric)

    def histogram(
        self, metric: str, value: float, tags: list[str] | None = None
    ) -> None:
        """Record a histogram metric."""
        if self.enabled and self.statsd:
            try:
                self.statsd.histogram(metric, value=value, tags=tags or [])
            except Exception as e:
                logger.debug("DataDog metric failed", error=str(e), metric=metric)

    def gauge(self, metric: str, value: float, tags: list[str] | None = None) -> None:
        """Set a gauge metric."""
        if self.enabled and self.statsd:
            try:
                self.statsd.gauge(metric, value=value, tags=tags or [])
            except Exception as e:
                logger.debug("DataDog metric failed", error=str(e), metric=metric)


# Global metrics instance (lazy initialization)
_metrics_instance = None


def get_metrics() -> DataDogMetrics:
    """Get the global metrics instance, creating it if needed."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = DataDogMetrics()
    return _metrics_instance


def record_real_agent_execution(
    agent_type: str, node_name: str, duration: float, success: bool
) -> None:
    """Record real agent execution metrics."""
    status = "success" if success else "failure"
    metrics = get_metrics()
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
    metrics = get_metrics()
    metrics.gauge(
        "universal_framework.circuit_breaker_status",
        float(status_code),
        tags=[f"agent_type:{agent_type}"],
    )


def record_langsmith_trace(
    endpoint: str, status: str, correlation_success: bool
) -> None:
    """Record LangSmith API trace metrics."""
    metrics = get_metrics()
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
    metrics = get_metrics()
    metrics.increment(
        "universal_framework.trace_correlation_success", tags=[f"platform:{platform}"]
    )
