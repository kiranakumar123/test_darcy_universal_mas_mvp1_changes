"""
Enterprise logging configuration for Universal Framework
Sets up structlog with JSON output and enterprise compliance
"""

import logging
from typing import Any

try:
    import structlog
except ImportError:
    structlog = None

from ..core.logging_foundation import get_safe_logger


def setup_structlog(log_level: str = "INFO") -> None:
    """Configure structlog for enterprise JSON logging

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if structlog is None:
        # Structlog not available, configure basic logging
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=getattr(logging, log_level.upper()),
        )
        return

    # Clear any existing configuration
    structlog.reset_defaults()

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=None,
        level=getattr(logging, log_level.upper()),
    )

    # Configure structlog for JSON output
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_enterprise_logger_config() -> dict[str, Any]:
    """Get enterprise logging configuration"""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
        },
        "loggers": {
            "universal_framework": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": True,
            },
        },
    }


# CRITICAL: Call this at application startup


def initialize_enterprise_logging() -> None:
    """Initialize enterprise logging configuration"""
    setup_structlog()

    # Log initialization success
    logger = get_safe_logger("logging_config")
    logger.info(
        "enterprise_logging_initialized",
        framework_version="3.1.0",
        compliance_frameworks=["SOC2", "ISO27001", "GDPR"],
    )
