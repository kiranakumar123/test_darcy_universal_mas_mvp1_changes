"""
Application startup configuration for Universal Framework.

This module ensures proper initialization order and prevents circular imports
by configuring shared resources at application startup.
"""

from __future__ import annotations

import logging


def configure_application_logging() -> None:
    """Configure application-wide logging during startup.

    This should be called once at application startup, before any other
    framework components are imported or initialized.
    """
    # Configure the core logging foundation
    from .core.logging_foundation import configure_structlog_once

    configure_structlog_once()

    # Set up any additional application-specific logging configuration
    logging.getLogger("universal_framework").setLevel(logging.INFO)


def initialize_framework() -> None:
    """Initialize the Universal Framework in the correct order.

    This function ensures that shared dependencies are initialized before
    any circular imports can occur.
    """
    # Step 1: Configure logging foundation
    configure_application_logging()

    # Step 2: Initialize other shared resources as needed
    # (Add other initialization steps here as the framework grows)

    # Framework is now safe to use
    logging.getLogger("universal_framework.startup").info(
        "Universal Framework initialized successfully"
    )
