"""LangSmith tracing middleware leveraging existing infrastructure."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from langsmith import trace
from starlette.middleware.base import BaseHTTPMiddleware

from universal_framework.compliance.pii_detector import PIIDetector

# Privacy logging now handled via dependency injection
from universal_framework.monitoring.performance import (
    record_langsmith_trace,
    record_trace_correlation_success,
)
from universal_framework.observability.enterprise_langsmith import (
    LangSmithCircuitBreaker,
)
from universal_framework.observability.logging_contracts import LoggingFactory
from universal_framework.observability.trace_correlation import (
    CrossPlatformTraceCorrelator,
)

logger = LoggingFactory.create_observability_logger("langsmith_middleware")


class LangSmithAPITracingMiddleware(BaseHTTPMiddleware):
    """LangSmith API tracing using existing infrastructure."""

    def __init__(
        self,
        app: Any,
        pii_detector: PIIDetector,
        circuit_breaker: LangSmithCircuitBreaker,
    ) -> None:
        super().__init__(app)
        self.pii_detector = pii_detector
        self.circuit_breaker = circuit_breaker
        # Privacy logging now handled by UniversalFrameworkLogger
        self.trace_correlator = CrossPlatformTraceCorrelator(pii_detector)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add LangSmith tracing to existing OpenTelemetry instrumentation."""

        session_id = request.headers.get("X-Session-ID", "anonymous")
        session_hash = self.pii_detector.hash_session_id(session_id)

        trace_metadata = {
            "session_hash": session_hash,
            "endpoint": request.url.path,
            "method": request.method,
            "api_tracing": True,
        }

        safe_metadata = self.pii_detector.redact_metadata(trace_metadata)

        start_time = time.time()
        response: Response | None = None
        try:
            async with self.circuit_breaker:
                otel_context = self.trace_correlator.get_current_trace_context(
                    session_id
                )
                enhanced_metadata = {
                    **safe_metadata,
                    "otel_correlation": otel_context.get("opentelemetry", {}),
                    "correlation_timestamp": otel_context.get("correlation_timestamp"),
                    "cross_platform_correlated": True,
                }

                with trace(
                    name=f"api_{request.method}_{request.url.path}",
                    session_id=session_hash,
                    metadata=enhanced_metadata,
                    tags=[
                        "api_request",
                        "langsmith_integration",
                        "cross_platform",
                    ],
                ) as tracer:
                    response = await call_next(request)
                    execution_time = time.time() - start_time
                    tracer.metadata.update(
                        {
                            "status_code": response.status_code,
                            "duration_ms": execution_time * 1000,
                            "correlation_success": True,
                            "otel_trace_id": otel_context.get("opentelemetry", {}).get(
                                "trace_id"
                            ),
                            "otel_span_id": otel_context.get("opentelemetry", {}).get(
                                "span_id"
                            ),
                        }
                    )

                    try:
                        if tracer.id:
                            self.trace_correlator.add_correlation_to_langsmith_trace(
                                tracer.id, otel_context
                            )
                    except Exception as correlation_exc:  # noqa: BLE001
                        logger.log_error(
                            error_type="langsmith_correlation_failure",
                            error_message=str(correlation_exc),
                            context={"endpoint": request.url.path},
                        )

                    # Record metrics with DataDog
                    record_langsmith_trace(
                        endpoint=request.url.path,
                        status="success",
                        correlation_success=True,
                    )
                    record_trace_correlation_success(platform="api")
        except Exception as exc:  # noqa: BLE001
            if response is None:
                response = await call_next(request)
            try:
                failure_context = self.trace_correlator.get_current_trace_context(
                    session_id
                )
                correlation_info = failure_context.get("opentelemetry", {})
            except Exception:  # noqa: BLE001
                correlation_info = {}
            logger.log_error(
                error_type="langsmith_api_tracing_failed",
                error_message=str(exc),
                context={"endpoint": request.url.path},
            )
            self.privacy_logger.log_session_event(
                session_id=session_id,
                event="langsmith_trace_failure",
                metadata={
                    "error": str(exc),
                    "endpoint": request.url.path,
                    "otel_trace_id": correlation_info.get("trace_id"),
                    "correlation_attempted": True,
                },
            )
            record_langsmith_trace(
                endpoint=request.url.path, status="failure", correlation_success=False
            )

        if hasattr(response, "headers"):
            response.headers["X-LangSmith-Session"] = session_hash

        return response
