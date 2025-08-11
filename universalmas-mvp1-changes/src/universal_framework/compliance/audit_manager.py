"""Backward compatibility wrapper for EnterpriseAuditManager.

This module provides backward compatibility for existing code while delegating
to the new LangSmith-first audit manager in the observability module.
"""

from __future__ import annotations

import asyncio
import functools
from typing import Any

from .privacy_logger import PrivacySafeLogger


def _sync_wrapper(async_func):
    """Decorator to convert async functions to sync for backward compatibility."""

    @functools.wraps(async_func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new event loop
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                    return future.result()
            else:
                return loop.run_until_complete(async_func(*args, **kwargs))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(async_func(*args, **kwargs))

    return wrapper


class EnterpriseAuditManager:
    """Backward compatibility wrapper for EnterpriseAuditManager.

    This class maintains the original sync API while delegating to the new
    LangSmith-first audit manager for enhanced observability and tracing.
    """

    def __init__(
        self, privacy_logger: PrivacySafeLogger, hash_salt: str | None = None
    ) -> None:
        """Initialize with backward compatibility for existing code."""
        self.privacy_logger = privacy_logger
        self.hash_salt = hash_salt or "default_enterprise_salt"

        # Lazy initialization for LangSmith components
        self._audit_manager = None
        self._langsmith_available = None

        # Backward compatibility properties
        self.audit_registry: dict[str, dict[str, Any]] = {}
        self.compliance_flags = self._initialize_compliance_flags()
        self.security_events: list[dict[str, Any]] = []
        self.audit_events: list[dict[str, Any]] = []
        self.performance_threshold_ms = 5.0

    def _check_langsmith_availability(self) -> bool:
        """Check if LangSmith dependencies are available."""
        if self._langsmith_available is not None:
            return self._langsmith_available

        try:
            from ..observability.enterprise_audit import (
                EnterpriseAuditManager,
                EnterpriseLangSmithConfig,
            )

            self._langsmith_available = True
            return True
        except ImportError:
            self._langsmith_available = False
            return False

    def _get_audit_manager(self):
        """Lazy initialization of the LangSmith audit manager."""
        if self._audit_manager is not None:
            return self._audit_manager

        if not self._check_langsmith_availability():
            raise ImportError(
                "LangSmith dependencies not available. "
                "Install langchain_core and other required packages to use enhanced features."
            )

        from ..observability.enterprise_audit import (
            EnterpriseAuditManager,
            EnterpriseLangSmithConfig,
        )

        config = EnterpriseLangSmithConfig()
        self._audit_manager = EnterpriseAuditManager(
            privacy_logger=self.privacy_logger, langsmith_config=config
        )
        return self._audit_manager

    def _initialize_compliance_flags(self) -> dict[str, bool]:
        """Initialize enterprise compliance tracking flags."""
        return {
            "gdpr_article_25": True,
            "gdpr_article_32": True,
            "soc2_cc6_1": True,
            "iso_27001_a12": True,
        }

    @_sync_wrapper
    async def log_operation(
        self, operation: str, session_id: str, metadata: dict[str, Any]
    ) -> str:
        """Create immutable audit log entry (backward compatible sync interface)."""
        audit_manager = self._get_audit_manager()
        return await audit_manager.log_operation(operation, session_id, metadata)

    @_sync_wrapper
    async def verify_audit_integrity(self, audit_id: str) -> bool:
        """Verify stored audit entry integrity (backward compatible sync interface)."""
        audit_manager = self._get_audit_manager()
        return await audit_manager.verify_audit_integrity(audit_id)

    def track_agent_execution(
        self,
        agent_name: str,
        session_id: str,
        execution_context: dict[str, Any],
        performance_metrics: dict[str, float],
        success: bool = True,
        error_message: str | None = None,
    ) -> str:
        """Track agent execution with comprehensive audit trail (backward compatible sync interface)."""

        @_sync_wrapper
        async def _async_track():
            audit_manager = self._get_audit_manager()
            return await audit_manager.track_agent_execution(
                agent_name=agent_name,
                session_id=session_id,
                execution_context=execution_context,
                performance_metrics=performance_metrics,
                success=success,
                error_message=error_message,
            )

        return _async_track()

    def track_compliance_event(
        self,
        event_type: str,
        session_id: str,
        compliance_data: dict[str, Any],
        privacy_level: str = "standard",
    ) -> str:
        """Track compliance events with enterprise audit trail (backward compatible sync interface)."""

        @_sync_wrapper
        async def _async_track():
            audit_manager = self._get_audit_manager()
            return await audit_manager.track_compliance_event(
                event_type=event_type,
                session_id=session_id,
                compliance_data=compliance_data,
                privacy_level=privacy_level,
            )

        return _async_track()

    def log_security_event(
        self,
        session_id: str,
        event_type: str,
        source_agent: str,
        details: dict[str, Any],
    ) -> None:
        """Log security event (backward compatible sync interface)."""

        @_sync_wrapper
        async def _async_log():
            audit_manager = self._get_audit_manager()
            return await audit_manager.log_security_event(
                session_id=session_id,
                event_type=event_type,
                source_agent=source_agent,
                details=details,
            )

        return _async_log()

    def get_compliance_report(self, session_id: str) -> dict[str, Any]:
        """Generate compliance report for session (backward compatible sync interface)."""

        @_sync_wrapper
        async def _async_get():
            audit_manager = self._get_audit_manager()
            return await audit_manager.get_compliance_report(session_id)

        return _async_get()

    def get_audit_trail(
        self,
        session_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        criteria: dict[str, Any] | None = None,
        format: str = "json",
    ) -> dict[str, Any]:
        """Get audit trail with filtering (backward compatible sync interface)."""

        @_sync_wrapper
        async def _async_get():
            audit_manager = self._get_audit_manager()
            return await audit_manager.get_audit_trail(
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                criteria=criteria,
                format=format,
            )

        return _async_get()

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get audit manager performance metrics (backward compatible sync interface)."""

        @_sync_wrapper
        async def _async_get():
            audit_manager = self._get_audit_manager()
            return await audit_manager.get_performance_metrics()

        return _async_get()

    def health_check(self) -> bool:
        """Health check for compliance logging infrastructure (backward compatible sync interface)."""

        @_sync_wrapper
        async def _async_check():
            audit_manager = self._get_audit_manager()
            return await audit_manager.health_check_with_langsmith_integration()

        return _async_check()

    # Migration helper properties for accessing the async implementation
    @property
    def async_manager(self):
        """Access to the underlying async LangSmith-first audit manager.

        Use this property to access the full async API with LangSmith integration
        when migrating code to async patterns.
        """
        return self._get_audit_manager()

    def get_migration_info(self) -> dict[str, Any]:
        """Get information about migrating to the async LangSmith-first API."""
        langsmith_available = self._check_langsmith_availability()

        return {
            "status": "backward_compatibility_mode",
            "underlying_implementation": (
                "EnterpriseAuditManager" if langsmith_available else "fallback_mode"
            ),
            "langsmith_available": langsmith_available,
            "migration_recommendation": (
                "Use .async_manager property for full async API"
                if langsmith_available
                else "Install langchain_core for enhanced features"
            ),
            "langsmith_integration": (
                "available_via_async_manager"
                if langsmith_available
                else "unavailable_missing_dependencies"
            ),
            "cost_attribution": (
                "available_via_async_manager"
                if langsmith_available
                else "unavailable_missing_dependencies"
            ),
            "trace_correlation": (
                "available_via_async_manager"
                if langsmith_available
                else "unavailable_missing_dependencies"
            ),
            "performance_monitoring": (
                "enhanced_in_async_implementation"
                if langsmith_available
                else "basic_fallback_mode"
            ),
            "migration_guide": "See docs/MIGRATION_GUIDE.md",
            "required_dependencies": (
                ["langchain_core"]
                if not langsmith_available
                else "all_dependencies_available"
            ),
        }
