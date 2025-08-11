"""
Core logging foundation for Universal Framework.

This module provides the foundational logging infrastructure that can be safely
imported by both observability and compliance modules without circular dependencies.
"""

from __future__ import annotations

import logging
import os
from typing import Any

try:
    import structlog
except ImportError:
    structlog = None

# Global structlog configuration flag
_STRUCTLOG_CONFIGURED = False


def configure_structlog_once() -> None:
    """Configure structlog globally, but only once during application startup."""
    global _STRUCTLOG_CONFIGURED

    if _STRUCTLOG_CONFIGURED or structlog is None:
        return

    try:
        # Configure structlog with safe, non-recursive settings
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        _STRUCTLOG_CONFIGURED = True

    except ImportError:
        # Fallback to standard logging if structlog not available
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        _STRUCTLOG_CONFIGURED = True


def get_safe_logger(component_name: str) -> Any:
    """Get a safely configured logger instance.

    This function ensures structlog is configured before creating loggers,
    preventing recursion issues during module initialization.
    """
    configure_structlog_once()

    if structlog is not None:
        return structlog.get_logger(component_name)
    else:
        return logging.getLogger(component_name)


class SafeEnvironmentConfig:
    """Lazy-loaded environment configuration to avoid recursion during imports."""

    _instance: SafeEnvironmentConfig | None = None
    _config_cache: dict[str, Any] = {}

    def __new__(cls) -> SafeEnvironmentConfig:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        """Get environment variable with caching to avoid repeated os.getenv calls."""
        if key not in self._config_cache:
            try:
                value = os.getenv(key, default)
                # Convert common types
                if isinstance(default, bool):
                    self._config_cache[key] = (
                        value.lower() in ("true", "1", "yes", "on")
                        if value
                        else default
                    )
                elif isinstance(default, int | float):
                    self._config_cache[key] = type(default)(value) if value else default
                else:
                    self._config_cache[key] = value
            except (ValueError, TypeError, AttributeError):
                self._config_cache[key] = default

        return self._config_cache[key]


# Global singleton for safe environment access
env_config = SafeEnvironmentConfig()
