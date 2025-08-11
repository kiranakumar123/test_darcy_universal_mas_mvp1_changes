"""Universal Multi-Agent System Framework with integrated components."""

from __future__ import annotations

# Initialize framework in correct order to prevent circular imports
from .startup import initialize_framework

initialize_framework()

from .config.feature_flags import feature_flags
from .contracts.state import UniversalWorkflowState, WorkflowPhase
from .observability.logging_config import initialize_enterprise_logging
from .workflow.builder import (
    create_development_workflow,
    create_enhanced_workflow,
    create_production_workflow,
    create_streamlined_workflow,
    create_testing_workflow,
)

# Only initialize enterprise logging if enabled
# Temporarily disabled to avoid structlog dependency issues
# if feature_flags.is_enabled("ENTERPRISE_FEATURES"):
#     initialize_enterprise_logging()

# Conditional configuration imports
try:
    from .config.factory import (
        create_llm_config,  # noqa: F401 -- re-exported
        setup_observability,  # noqa: F401 -- re-exported
    )

    CONFIG_AVAILABLE = True
except ImportError as e:  # pragma: no cover - optional component
    import warnings

    warnings.warn(
        f"Configuration system not available: {e}",
        ImportWarning,
        stacklevel=2,
    )
    CONFIG_AVAILABLE = False

# Conditional real agent imports
try:
    from .agents.requirements_agent import real_requirements_collector
    from .llm.providers import LLMConfig, OpenAIProvider
    from .llm.tools import (
        EmailValidationTool,
        RequirementsExtractionTool,
        StateAccessTool,
    )

    REAL_AGENTS_AVAILABLE = True
except ImportError as e:  # pragma: no cover - optional component
    import warnings

    warnings.warn(
        f"Real agents not available: {e}. Install missing dependencies.",
        ImportWarning,
        stacklevel=2,
    )
    REAL_AGENTS_AVAILABLE = False
    real_requirements_collector = None
    OpenAIProvider = None
    LLMConfig = None
    EmailValidationTool = None
    RequirementsExtractionTool = None
    StateAccessTool = None

# Build public export list dynamically
__all__ = [
    "UniversalWorkflowState",
    "WorkflowPhase",
    "create_streamlined_workflow",
    "create_enhanced_workflow",
    "create_development_workflow",
    "create_production_workflow",
    "create_testing_workflow",
]

if CONFIG_AVAILABLE:
    __all__.extend(["create_llm_config", "setup_observability"])

if REAL_AGENTS_AVAILABLE:
    __all__.extend(
        [
            "real_requirements_collector",
            "OpenAIProvider",
            "LLMConfig",
            "EmailValidationTool",
            "RequirementsExtractionTool",
            "StateAccessTool",
        ]
    )

# Expose availability flags
__all__.extend(["REAL_AGENTS_AVAILABLE", "CONFIG_AVAILABLE"])

__all__.extend(
    [
        "__version__",
        "__author__",
        "__email__",
        "DEFAULT_SESSION_TTL",
        "DEFAULT_API_TIMEOUT",
        "DEFAULT_REDIS_DB",
        "ENTERPRISE_FEATURES",
    ]
)

__version__ = "1.0.0"
__author__ = "Universal Framework Team"

__email__ = "team@universal-framework.dev"

# Package-level configuration

DEFAULT_SESSION_TTL = 86400  # 24 hours in seconds
DEFAULT_API_TIMEOUT = 30  # 30 seconds
DEFAULT_REDIS_DB = 0

# Enterprise features respect safe mode configuration
ENTERPRISE_FEATURES = {
    "audit_logging": feature_flags.is_enabled("ENTERPRISE_AUDIT_VALIDATION"),
    "compliance_validation": feature_flags.is_enabled("ENTERPRISE_FEATURES"),
    "security_monitoring": feature_flags.is_enabled("ENTERPRISE_FEATURES"),
    "performance_tracking": feature_flags.is_enabled("LANGSMITH_TRACING"),
}


def get_package_status() -> dict[str, bool]:
    """Return availability status for optional components."""

    return {
        "core_framework": True,
        "config_system": CONFIG_AVAILABLE,
        "real_agents": REAL_AGENTS_AVAILABLE,
        "version": __version__,
    }


def validate_package_imports() -> list[str]:
    """Validate package imports and return a list of issues, if any."""

    issues: list[str] = []
    try:
        _ = UniversalWorkflowState(session_id="test", user_id="test", auth_token="test")
    except Exception as e:  # pragma: no cover - diagnostic helper
        issues.append(f"Core state import failed: {e}")

    try:
        _ = create_testing_workflow()
    except Exception as e:  # pragma: no cover - diagnostic helper
        issues.append(f"Core workflow import failed: {e}")

    if CONFIG_AVAILABLE and feature_flags.is_enabled("LANGSMITH_TRACING"):
        try:
            _ = setup_observability()
        except Exception as e:  # pragma: no cover - diagnostic helper
            issues.append(f"Configuration system failed: {e}")

    if REAL_AGENTS_AVAILABLE:
        try:
            _ = OpenAIProvider()
        except Exception as e:  # pragma: no cover - diagnostic helper
            issues.append(f"Real agent system failed: {e}")

    return issues


__all__.extend(["get_package_status", "validate_package_imports"])
