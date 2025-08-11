"""Safe mode implementations for compliance components."""

from __future__ import annotations

from typing import Any

# Use safe logging foundation to prevent circular imports
from ..core.logging_foundation import get_safe_logger


class SafeModeAuditManager:
    """Safe mode audit manager with minimal logging."""

    def __init__(self, logger: Any | None = None) -> None:
        """Initialize safe mode audit manager with dependency injection."""
        self.logger = logger or get_safe_logger("safe_mode")

    def log_security_event(
        self,
        session_id: str,
        event_type: str,
        source_agent: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log security events in safe mode."""
        self.logger.info(
            "safe_mode_security_event",
            session_id=session_id,
            event_type=event_type,
            source_agent=source_agent,
            details=details or {},
            safe_mode=True,
        )

    def log_state_update_sync(
        self,
        session_id: str,
        source_agent: str,
        event: str,
        fields_updated: list[str],
        audit_id: str,
    ) -> None:
        """Log state updates in safe mode."""
        self.logger.info(
            "safe_mode_state_update",
            session_id=session_id,
            source_agent=source_agent,
            event=event,
            fields_updated=fields_updated,
            audit_id=audit_id,
            safe_mode=True,
        )

    def log_agent_execution(self, *args, **kwargs) -> None:
        """Safe mode: Log minimal agent execution without enterprise audit."""
        try:
            self.logger.info("safe_mode_agent_execution", minimal_audit=True)
        except Exception:
            pass  # Fail silently in safe mode

    def track_agent_execution(self, *args, **kwargs) -> None:
        """Safe mode: Track agent execution without enterprise audit."""
        try:
            self.logger.info("safe_mode_agent_tracking", minimal_audit=True)
        except Exception:
            pass  # Fail silently in safe mode

    def track_compliance_event(self, *args, **kwargs) -> None:
        """Safe mode: Track compliance events without enterprise audit."""
        try:
            self.logger.info("safe_mode_compliance_tracking", minimal_audit=True)
        except Exception:
            pass  # Fail silently in safe mode

    def get_performance_metrics(self, *args, **kwargs) -> dict:
        """Safe mode: Return minimal performance metrics."""
        return {"safe_mode": True, "enterprise_metrics": False, "metrics": {}}

    def health_check(self, *args, **kwargs) -> bool:
        """Safe mode: Always return healthy status."""
        return True

    async def log_operation(self, *args, **kwargs) -> None:
        """Safe mode: Log minimal operation info."""
        try:
            self.logger.info("safe_mode_operation", minimal_audit=True)
        except Exception:
            pass  # Fail silently in safe mode

    async def verify_audit_integrity(self, audit_id: str) -> bool:
        """Safe mode: Always return True for audit integrity."""
        return True

    def get_compliance_report(self, *args, **kwargs) -> dict:
        """Safe mode: Return minimal compliance report."""
        return {
            "safe_mode": True,
            "enterprise_audit": False,
            "status": "minimal_audit_active",
        }

    def get_audit_trail(self, *args, **kwargs) -> dict:
        """Safe mode: Return minimal audit trail."""
        return {"safe_mode": True, "enterprise_audit": False, "audit_trail": []}

    async def log_state_update(
        self,
        session_hash: str,
        source_agent: str,
        attempted_fields: list[str],
        authorized_fields: list[str],
        unauthorized_fields: list[str] | None = None,
        severity: str = "MEDIUM",
    ) -> None:
        """Async wrapper for state update logging in safe mode."""
        self.logger.info(
            "safe_mode_state_update_async",
            session_hash=session_hash,
            source_agent=source_agent,
            attempted_fields=attempted_fields,
            authorized_fields=authorized_fields,
            unauthorized_fields=unauthorized_fields or [],
            severity=severity,
            safe_mode=True,
        )
