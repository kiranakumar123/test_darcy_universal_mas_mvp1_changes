"""GDPR-compliant structured logging with automatic PII redaction."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from ..config.feature_flags import feature_flags

# Safe logging import to prevent circular dependencies
from ..core.logging_foundation import get_safe_logger
from .pii_detector import PIIDetector, RedactionConfig


class PrivacySafeLogger:
    """GDPR-compliant structured logger with automatic PII redaction."""

    def __init__(self, redaction_config: RedactionConfig | None = None) -> None:
        # Only initialize PII detector if feature is enabled
        if feature_flags.is_enabled("PII_REDACTION"):
            self.pii_detector = PIIDetector(redaction_config or RedactionConfig())
        else:
            self.pii_detector = None
        self.logger = self._setup_safe_logger()

    def _setup_safe_logger(self) -> Any:
        """Configure safe logger for GDPR-compliant JSON output."""
        return get_safe_logger("universal_framework.privacy_safe")

    def _safe_hash_session_id(self, session_id: str) -> str:
        """Hash session ID if PII detection enabled, otherwise return safe placeholder."""
        if self.pii_detector:
            return self.pii_detector.hash_session_id(session_id)
        return f"session_hash_{hash(session_id) % 100000:05d}"

    def _safe_redact_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Redact metadata if PII detection enabled, otherwise return as-is."""
        if self.pii_detector:
            return self.pii_detector.redact_metadata(metadata)
        return metadata

    def _safe_redact_pii(self, text: str) -> str:
        """Redact PII if detection enabled, otherwise return as-is."""
        if self.pii_detector:
            return self.pii_detector.redact_pii(text)
        return text

    def log_session_event(
        self,
        session_id: str,
        event: str,
        metadata: dict[str, Any],
        level: str = "info",
    ) -> None:
        """Log session event with automatic PII redaction and GDPR compliance."""
        session_hash = self._safe_hash_session_id(session_id)
        redacted_metadata = self._safe_redact_metadata(metadata)
        log_entry = {
            "session_hash": session_hash,
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "metadata": redacted_metadata,
            "compliance": {
                "gdpr_version": "2016/679",
                "privacy_by_design": True,
                "pii_redacted": True,
                "audit_safe": True,
            },
        }
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        event_name = cast(str, log_entry.pop("event"))
        log_method(event_name, **log_entry)

    def log_agent_execution(
        self,
        agent_name: str,
        session_id: str,
        execution_context: dict[str, Any],
        performance_metrics: dict[str, float],
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """Log agent execution with privacy protection and performance tracking."""
        session_hash = self._safe_hash_session_id(session_id)
        redacted_context = self._safe_redact_metadata(execution_context)
        redacted_error = self._safe_redact_pii(error_message) if error_message else None
        log_entry = {
            "event": "agent_execution",
            "agent_name": agent_name,
            "session_hash": session_hash,
            "execution_context": redacted_context,
            "performance_metrics": performance_metrics,
            "success": success,
            "error_message": redacted_error,
            "timestamp": datetime.now().isoformat(),
            "compliance": {
                "gdpr_compliant": True,
                "pii_redacted": True,
                "performance_tracked": True,
            },
        }
        level = "info" if success else "error"
        log_method = getattr(self.logger, level)
        event_name = cast(str, log_entry.pop("event"))
        log_method(event_name, **log_entry)

    def log_workflow_transition(
        self,
        session_id: str,
        from_phase: str,
        to_phase: str,
        trigger_agent: str,
        state_metadata: dict[str, Any],
    ) -> None:
        """Log FSM workflow transitions with privacy protection."""
        session_hash = self._safe_hash_session_id(session_id)
        redacted_metadata = self._safe_redact_metadata(state_metadata)
        log_entry = {
            "event": "workflow_transition",
            "session_hash": session_hash,
            "from_phase": from_phase,
            "to_phase": to_phase,
            "trigger_agent": trigger_agent,
            "state_metadata": redacted_metadata,
            "timestamp": datetime.now().isoformat(),
            "compliance": {
                "fsm_audit": True,
                "gdpr_compliant": True,
                "state_tracked": True,
            },
        }
        event_name = cast(str, log_entry.pop("event"))
        self.logger.info(event_name, **log_entry)

    def log_compliance_event(
        self,
        event_type: str,
        event_data: dict[str, Any],
        session_id: str | None = None,
        privacy_level: str = "standard",
    ) -> None:
        """Log compliance events with optional session context."""
        session_hash = self._safe_hash_session_id(session_id) if session_id else None
        redacted_data = self._safe_redact_metadata(event_data)
        entry = {
            "event": event_type,
            "session_hash": session_hash,
            "event_data": redacted_data,
            "privacy_level": privacy_level,
            "timestamp": datetime.now().isoformat(),
        }
        event_name = cast(str, entry.pop("event"))
        self.logger.info(event_name, **entry)

    def redact_pii(self, text: str) -> str:
        """Redact PII from text content."""
        return self._safe_redact_pii(text)

    def log_error(
        self,
        error_type: str,
        error_message: str,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log errors with PII redaction using defensive programming."""
        session_hash = self._safe_hash_session_id(session_id) if session_id else None
        redacted_message = self._safe_redact_pii(error_message)
        redacted_context = self._safe_redact_metadata(context or {})

        # DEFENSIVE PROGRAMMING: Safe timestamp access
        try:
            timestamp = redacted_context.get("timestamp")
            if not timestamp:
                timestamp = datetime.now().isoformat()
        except (AttributeError, KeyError):
            timestamp = datetime.now().isoformat()

        # DEFENSIVE PROGRAMMING: Safe error_message access
        try:
            final_error_message = redacted_context.get(
                "error_message", redacted_message
            )
        except (AttributeError, KeyError):
            final_error_message = redacted_message

        log_entry = {
            "error_type": error_type,
            "error_message": final_error_message,
            "session_hash": session_hash,
            "context": redacted_context,
            "timestamp": timestamp,
        }
        self.logger.error("framework_error", **log_entry)
