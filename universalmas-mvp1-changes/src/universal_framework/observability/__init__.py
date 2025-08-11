"""
Universal Framework Observability Module
Clean modular architecture with protocol-based composition.
"""

# Import feature flags to check safe mode before loading enterprise components
from ..config.feature_flags import feature_flags

# Specialized utilities
from .agent_execution_logger import AgentExecutionLogger

# Core implementations for advanced usage
from .langsmith_tracer import LangSmithTracer
from .logging_contracts import LoggingFactory

# MODERN LOGGER: Using enhanced protocol-based implementation
from .modern_logger import ModernUniversalFrameworkLogger as UniversalFrameworkLogger
from .performance_logger import PerformanceLogger

# LEGACY SUPPORT: Temporarily disabled due to encoding issues
# from .unified_logger import UniversalFrameworkLogger
# Protocol interfaces for dependency injection and testing
from .protocols import (
    LogEvent,
    LoggerProtocol,
    LogLevel,
    PrivacyFilterProtocol,
    TraceContext,
    TracerProtocol,
)

# Always-available metrics (safe mode)
from .simple_metrics import (
    SimpleMetricsCollector,
    get_metrics_summary,
    measure_agent_execution,
    measure_routing_operation,
)
from .structured_logger import StructuredLogger

# Version and metadata
__version__ = "3.1.0"
__all__ = [
    "UniversalFrameworkLogger",
    "AgentExecutionLogger",
    "LogEvent",
    "LogLevel",
    "TracerProtocol",
    "LoggerProtocol",
    "PrivacyFilterProtocol",
    "TraceContext",
    "LangSmithTracer",
    "StructuredLogger",
    "LoggingFactory",
    "PerformanceLogger",
    "SimpleMetricsCollector",
    "get_metrics_summary",
    "measure_agent_execution",
    "measure_routing_operation",
]

# Conditionally import enterprise components only if safe mode allows
if not feature_flags.is_safe_mode() and feature_flags.is_enabled("ENTERPRISE_FEATURES"):
    from .enterprise_audit import EnterpriseAuditManager
    from .langsmith_middleware import LangSmithAPITracingMiddleware
    from .trace_correlation import CrossPlatformTraceCorrelator
else:
    # Provide safe mode stubs to prevent import errors
    EnterpriseAuditManager = None
    LangSmithAPITracingMiddleware = None
    CrossPlatformTraceCorrelator = None

# Conditionally import LangSmith components only if tracing is enabled
if not feature_flags.is_safe_mode() and feature_flags.is_enabled("LANGSMITH_TRACING"):
    from .enterprise_langsmith import (
        EnterpriseLangSmithConfig,
        LangSmithCircuitBreaker,
        LangSmithCircuitBreakerError,
        create_2025_standard_metadata,
        create_enterprise_langsmith_client,
        enhance_trace_real_agent_execution,
        setup_enterprise_langsmith_tracing,
    )
else:
    # Provide safe mode stubs to prevent import errors
    EnterpriseLangSmithConfig = None
    LangSmithCircuitBreaker = None
    LangSmithCircuitBreakerError = None
    create_2025_standard_metadata = None
    create_enterprise_langsmith_client = None
    enhance_trace_real_agent_execution = None
    setup_enterprise_langsmith_tracing = None

__all__ = [
    "EnterpriseAuditManager",
    "SimpleMetricsCollector",
    "measure_agent_execution",
    "measure_routing_operation",
    "get_metrics_summary",
    "EnterpriseLangSmithConfig",
    "LangSmithCircuitBreaker",
    "LangSmithCircuitBreakerError",
    "create_enterprise_langsmith_client",
    "enhance_trace_real_agent_execution",
    "setup_enterprise_langsmith_tracing",
    "create_2025_standard_metadata",
    "LangSmithAPITracingMiddleware",
    "CrossPlatformTraceCorrelator",
    "UniversalFrameworkLogger",
    "LoggingFactory",
    "PerformanceLogger",
]
