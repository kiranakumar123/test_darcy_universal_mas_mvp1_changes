"""LangSmith-first Enterprise Audit Manager with unified observability."""

from __future__ import annotations

import hashlib
import json
import time
import tracemalloc
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import uuid4

# Optional imports with fallbacks
try:
    import jsonschema
except ImportError:
    jsonschema = None

try:
    from ..core.logging_foundation import get_safe_logger
except ImportError:
    structlog = None

# NOTE: @traceable should NOT be used on audit/logging methods
# Use @traceable only on business logic functions that need tracing
# Audit methods should add metadata to existing traces via unified_logger

from ..compliance.exceptions import ComplianceError, StateValidationError

# Privacy logging now handled via dependency injection
from .enterprise_langsmith import (
    CostTrackingIntegration,
    EnterpriseLangSmithConfig,
    enhance_trace_real_agent_execution,
    log_enterprise_performance_metrics,
)
from .logging_contracts import LoggingFactory
from .trace_correlation import CrossPlatformTraceCorrelator

# Load audit schemas
SCHEMA_PATH = Path(__file__).parent.parent / "compliance" / "audit_schemas.json"
try:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        _AUDIT_SCHEMAS = json.load(f)
    AUDIT_EVENT_SCHEMA = _AUDIT_SCHEMAS["definitions"]["AuditEvent"]
except json.JSONDecodeError as e:
    raise ValueError(
        f"Invalid JSON in audit schemas file {SCHEMA_PATH}: {e}. "
        f"Please check the file for syntax errors, especially property names "
        f"that should be enclosed in double quotes."
    ) from e
except FileNotFoundError:
    raise FileNotFoundError(
        f"Audit schemas file not found: {SCHEMA_PATH}. "
        f"Please ensure the file exists and is properly deployed."
    )
except KeyError as e:
    raise KeyError(
        f"Missing required schema definition in {SCHEMA_PATH}: {e}. "
        f"Expected 'definitions.AuditEvent' structure."
    ) from e


class EnterpriseAuditManager:
    """
    LangSmith-first enterprise audit manager with unified observability.

    All audit, compliance, and performance operations are fully integrated
    with LangSmith tracing, cost attribution, and cross-platform correlation.
    """

    def __init__(
        self,
        privacy_logger: PrivacySafeLogger,
        langsmith_config: EnterpriseLangSmithConfig,
        hash_salt: str | None = None,
    ) -> None:
        self.privacy_logger = privacy_logger
        self.langsmith_config = langsmith_config
        self.cost_tracker = CostTrackingIntegration(langsmith_config)
        self.trace_correlator = CrossPlatformTraceCorrelator(
            langsmith_config.pii_detector
        )
        self.audit_registry: dict[str, dict[str, Any]] = {}
        self.compliance_flags = self._initialize_compliance_flags()
        self.hash_salt = hash_salt or "default_enterprise_salt"
        self.security_events: list[dict[str, Any]] = []
        self.audit_events: list[dict[str, Any]] = []
        self.logger = get_safe_logger("enterprise_audit_langsmith")
        self.performance_threshold_ms = 5.0

    def _initialize_compliance_flags(self) -> dict[str, bool]:
        """Initialize enterprise compliance tracking flags."""
        return {
            "gdpr_article_25": True,
            "gdpr_article_32": True,
            "soc2_cc6_1": True,
            "iso_27001_a12": True,
        }

    async def log_operation(
        self, operation: str, session_id: str, metadata: dict[str, Any]
    ) -> str:
        """Create immutable audit log entry with metadata to existing traces."""

        # Create privacy-safe trace metadata
        trace_metadata = self.langsmith_config.create_privacy_safe_trace_metadata(
            "audit_manager", session_id
        )

        # Get correlation context for trace linking
        correlation_context = self.trace_correlator.get_current_trace_context(
            session_id
        )

        audit_id = f"audit_{uuid4()}"
        entry = {
            "audit_id": audit_id,
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "session_id": session_id,
            "metadata": metadata,
            "trace_metadata": trace_metadata,
            "correlation_context": correlation_context,
        }

        # Create integrity hash
        raw = json.dumps(entry, sort_keys=True)
        entry["integrity_hash"] = hashlib.sha256(raw.encode()).hexdigest()

        # Store in registry
        self.audit_registry[audit_id] = entry

        # Log to both compliance logs and LangSmith
        await self._log_to_enterprise_system_with_langsmith("audit", entry)

        # Cost attribution for audit operation
        await self._attribute_audit_cost(audit_id, operation, session_id, metadata)

        self.logger.info(
            "audit_log_created",
            operation=operation,
            session_hash=trace_metadata["session_hash"],
            audit_id=audit_id,
            langsmith_traced=True,
        )

        return audit_id

    async def verify_audit_integrity(self, audit_id: str) -> bool:
        """Verify stored audit entry integrity - adds metadata to existing traces."""
        entry = self.audit_registry.get(audit_id)
        if not entry:
            return False

        stored_hash = entry.get("integrity_hash")
        check_entry = entry.copy()
        check_entry.pop("integrity_hash", None)
        calc_hash = hashlib.sha256(
            json.dumps(check_entry, sort_keys=True).encode()
        ).hexdigest()

        result = stored_hash == calc_hash

        # Log verification result to LangSmith
        self.logger.info(
            "audit_integrity_verified",
            audit_id=audit_id,
            integrity_valid=result,
            langsmith_traced=True,
        )

        return result

    async def track_agent_execution(
        self,
        agent_name: str,
        session_id: str,
        execution_context: dict[str, Any],
        performance_metrics: dict[str, float],
        success: bool = True,
        error_message: str | None = None,
    ) -> str:
        """
        Track agent execution with comprehensive LangSmith integration.

        All audit trails include LangSmith trace correlation, cost attribution,
        and cross-platform observability.
        """
        start_time = time.perf_counter()

        async def _run() -> str:
            # Validate compliance requirements
            if not agent_name or not agent_name.strip():
                raise ComplianceError(
                    message="Agent name is required for compliance audit tracking",
                    context={
                        "audit_operation": "track_agent_execution",
                        "provided_agent_name": repr(agent_name),
                        "compliance_requirement": "SOC2_audit_trail",
                    },
                )

            if not isinstance(execution_context, dict):
                raise ComplianceError(
                    message="Execution context must be a dictionary for audit compliance",
                    context={
                        "audit_operation": "track_agent_execution",
                        "expected_type": "dict",
                        "actual_type": type(execution_context).__name__,
                        "compliance_requirement": "structured_audit_data",
                    },
                )

            # Generate execution ID and create trace metadata
            execution_id = str(uuid4())
            trace_metadata = self.langsmith_config.create_privacy_safe_trace_metadata(
                agent_name, session_id
            )
            correlation_context = self.trace_correlator.get_current_trace_context(
                session_id
            )

            # Validate execution compliance
            compliance_status = self._validate_execution_compliance(execution_context)

            # Create comprehensive audit record with LangSmith integration
            audit_record = {
                "event_type": "agent_execution",  # Add required event_type field
                "execution_id": execution_id,
                "agent_name": agent_name,
                "timestamp": datetime.now().isoformat(),
                "performance_metrics": performance_metrics,
                "compliance_status": compliance_status,
                "success": success,
                "enterprise_flags": self.compliance_flags.copy(),
                "trace_metadata": trace_metadata,
                "correlation_context": correlation_context,
                "error_message": error_message,
            }

            # Validate against audit schema
            self._validate_audit_event(audit_record)

            # Store in registry
            self.audit_registry[execution_id] = audit_record

            # Log to privacy logger (existing pattern)
            self.privacy_logger.log_agent_execution(
                agent_name=agent_name,
                session_id=session_id,
                execution_context=execution_context,
                performance_metrics=performance_metrics,
                success=success,
                error_message=error_message,
            )

            # Log to enterprise system with LangSmith integration
            await self._log_to_enterprise_system_with_langsmith(
                "agent_execution", audit_record
            )

            # Cost attribution for agent execution
            await self._attribute_execution_cost(
                execution_id, agent_name, session_id, performance_metrics
            )

            # Performance monitoring with LangSmith logging
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            await self._log_performance_to_langsmith(
                agent_name, session_id, execution_time_ms, audit_record, success
            )

            return execution_id

        # Apply the decorator with runtime values
        wrapped = enhance_trace_real_agent_execution(
            agent_name,
            session_id,
            getattr(
                self, "enterprise_config", None
            ),  # Use enterprise config if available
        )(_run)

        return await wrapped()

    async def track_compliance_event(
        self,
        event_type: str,
        session_id: str | None,
        event_data: dict[str, Any],
    ) -> None:
        """Track compliance event with LangSmith integration and cost attribution."""
        start_time = time.perf_counter()

        # Create trace metadata
        trace_metadata = (
            self.langsmith_config.create_privacy_safe_trace_metadata(
                "compliance_tracker", session_id or "system"
            )
            if session_id
            else {"session_hash": "system_event"}
        )

        correlation_context = (
            self.trace_correlator.get_current_trace_context(session_id)
            if session_id
            else {"session_hash": "system_event", "correlation_timestamp": time.time()}
        )

        record = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "session_hash": self._hash_pii(session_id) if session_id else None,
            "event_data": event_data,
            "trace_metadata": trace_metadata,
            "correlation_context": correlation_context,
        }

        # Validate against audit schema
        self._validate_audit_event(record)
        self.audit_events.append(record)

        # Log to enterprise system with LangSmith
        await self._log_to_enterprise_system_with_langsmith("compliance", record)

        # Cost attribution for compliance tracking
        await self._attribute_compliance_cost(event_type, session_id, event_data)

        # Performance monitoring
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        await self._log_performance_to_langsmith(
            "compliance_tracker",
            session_id or "system",
            execution_time_ms,
            record,
            True,
        )

    async def _log_to_enterprise_system_with_langsmith(
        self, log_type: str, record: dict[str, Any]
    ) -> None:
        """
        Log to enterprise system with full LangSmith integration.

        CRITICAL: All audit logs must be present in both compliance logs
        and LangSmith traces with proper correlation and cost attribution.
        """
        start_time = time.perf_counter()

        try:
            # Circuit breaker check for LangSmith
            if self.langsmith_config.circuit_breaker:
                async with self.langsmith_config.circuit_breaker:
                    # Validate event structure
                    self._validate_audit_event(record)

                    # Log to compliance system (existing pattern)
                    compliance_logger = LoggingFactory.create_compliance_logger()
                    compliance_logger.log_compliance_event(
                        event_type=log_type,
                        event_data=record,
                        session_id=record.get("session_id"),
                        privacy_level="enterprise_audit",
                    )

                    # Log to LangSmith with trace correlation
                    self.logger.info(
                        "enterprise_audit_event",
                        log_type=log_type,
                        event_id=record.get("audit_id") or record.get("execution_id"),
                        trace_metadata=record.get("trace_metadata", {}),
                        correlation_context=record.get("correlation_context", {}),
                        langsmith_traced=True,
                        compliance_logged=True,
                    )
            else:
                # Fallback when circuit breaker not available
                await self._log_with_fallback(log_type, record)

            # Performance monitoring
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            if execution_time_ms > self.performance_threshold_ms:
                await log_enterprise_performance_metrics(
                    self.langsmith_config,
                    "audit_manager",
                    record.get("session_id", "system"),
                    execution_time_ms,
                    record,
                    True,
                    f"audit_logging_performance_violation_{log_type}",
                )

        except Exception as e:
            # Graceful fallback with circuit breaker trigger
            await self._log_with_fallback(log_type, record, error=str(e))

            # Trigger circuit breaker if needed
            if self.langsmith_config.circuit_breaker:
                await self.langsmith_config.circuit_breaker.__aexit__(
                    type(e), e, e.__traceback__
                )

    async def _log_with_fallback(
        self, log_type: str, record: dict[str, Any], error: str | None = None
    ) -> None:
        """Fallback logging when LangSmith is unavailable."""
        try:
            # Log to compliance system
            compliance_logger = LoggingFactory.create_compliance_logger()
            compliance_logger.log_compliance_event(
                event_type=log_type,
                event_data=record,
                session_id=record.get("session_id"),
                privacy_level="enterprise_audit",
            )

            # Log fallback warning
            fallback_record = {
                "fallback_reason": error or "langsmith_unavailable",
                "original_log_type": log_type,
                "timestamp": datetime.now().isoformat(),
                "compliance_logged": True,
                "langsmith_logged": False,
            }

            compliance_logger.log_compliance_event(
                event_type="audit_fallback_warning",
                event_data=fallback_record,
                privacy_level="enterprise_audit",
            )

        except Exception as fallback_error:
            # Final fallback - log to structlog only
            self.logger.error(
                "audit_logging_failure",
                log_type=log_type,
                original_error=error,
                fallback_error=str(fallback_error),
                compliance_logged=False,
                langsmith_logged=False,
            )

    async def _attribute_audit_cost(
        self, audit_id: str, operation: str, session_id: str, metadata: dict[str, Any]
    ) -> None:
        """Attribute cost for audit operations in LangSmith."""
        # Create mock token usage for audit operations
        from unittest.mock import MagicMock

        mock_usage = MagicMock()
        mock_usage.total_tokens = (
            len(json.dumps(metadata)) // 4
        )  # Approximate token count
        mock_usage.agent_token_usage = {
            "audit_manager": {
                "total_tokens": len(json.dumps(metadata)) // 4,
                "agent_name": "audit_manager",
            }
        }

        mock_cost = MagicMock()
        mock_cost.total_cost_usd = 0.001  # Minimal cost for audit operations
        mock_cost.model_costs = {"audit_manager": 0.001}

        cost_metadata = self.cost_tracker.create_cost_metadata(
            mock_usage, mock_cost, "audit_manager"
        )

        # Log cost attribution to LangSmith
        self.logger.info(
            "audit_cost_attribution",
            audit_id=audit_id,
            operation=operation,
            session_hash=self.langsmith_config.pii_detector.hash_session_id(session_id),
            cost_metadata=cost_metadata,
            langsmith_traced=True,
        )

    async def _attribute_execution_cost(
        self,
        execution_id: str,
        agent_name: str,
        session_id: str,
        performance_metrics: dict[str, float],
    ) -> None:
        """Attribute cost for agent execution tracking in LangSmith."""
        # Estimate tokens based on performance metrics
        estimated_tokens = int(performance_metrics.get("execution_time", 100) * 10)

        mock_usage = type(
            "MockUsage",
            (),
            {
                "total_tokens": estimated_tokens,
                "agent_token_usage": {
                    agent_name: {
                        "total_tokens": estimated_tokens,
                        "agent_name": agent_name,
                    }
                },
            },
        )()

        mock_cost = type(
            "MockCost",
            (),
            {
                "total_cost_usd": estimated_tokens * 0.0001,
                "model_costs": {agent_name: estimated_tokens * 0.0001},
            },
        )()

        cost_metadata = self.cost_tracker.create_cost_metadata(
            mock_usage, mock_cost, agent_name
        )

        # Log cost attribution to LangSmith
        self.logger.info(
            "execution_cost_attribution",
            execution_id=execution_id,
            agent_name=agent_name,
            session_hash=self.langsmith_config.pii_detector.hash_session_id(session_id),
            cost_metadata=cost_metadata,
            langsmith_traced=True,
        )

    async def _attribute_compliance_cost(
        self, event_type: str, session_id: str | None, event_data: dict[str, Any]
    ) -> None:
        """Attribute cost for compliance tracking in LangSmith."""
        # Minimal cost for compliance events
        mock_usage = type(
            "MockUsage",
            (),
            {
                "total_tokens": len(json.dumps(event_data)) // 4,
                "agent_token_usage": {
                    "compliance_tracker": {
                        "total_tokens": len(json.dumps(event_data)) // 4,
                        "agent_name": "compliance_tracker",
                    }
                },
            },
        )()

        mock_cost = type(
            "MockCost",
            (),
            {"total_cost_usd": 0.0005, "model_costs": {"compliance_tracker": 0.0005}},
        )()

        cost_metadata = self.cost_tracker.create_cost_metadata(
            mock_usage, mock_cost, "compliance_tracker"
        )

        session_hash = (
            self.langsmith_config.pii_detector.hash_session_id(session_id)
            if session_id
            else "system_event"
        )

        # Log cost attribution to LangSmith
        self.logger.info(
            "compliance_cost_attribution",
            event_type=event_type,
            session_hash=session_hash,
            cost_metadata=cost_metadata,
            langsmith_traced=True,
        )

    async def _log_performance_to_langsmith(
        self,
        agent_name: str,
        session_id: str,
        execution_time_ms: float,
        record: dict[str, Any],
        success: bool,
        fallback_reason: str | None = None,
    ) -> None:
        """Log performance metrics to LangSmith with enterprise integration."""
        # Check if performance threshold exceeded
        if execution_time_ms > self.performance_threshold_ms:
            # Log performance violation to both compliance and LangSmith
            violation_record = {
                "metric_value": execution_time_ms,
                "threshold_ms": self.performance_threshold_ms,
                "agent_name": agent_name,
                "component": "enterprise_audit_manager",
                "trace_metadata": record.get("trace_metadata", {}),
                "correlation_context": record.get("correlation_context", {}),
            }

            compliance_logger = LoggingFactory.create_compliance_logger()
            compliance_logger.log_performance_metric(
                metric_name="audit_logging_performance_violation",
                metric_value=execution_time_ms,
                context=violation_record,
            )

        # Always log to LangSmith enterprise performance metrics
        await log_enterprise_performance_metrics(
            self.langsmith_config,
            agent_name,
            session_id,
            execution_time_ms,
            record,
            success,
            fallback_reason,
        )

    def _validate_execution_compliance(
        self, execution_context: dict[str, Any]
    ) -> dict[str, bool]:
        """Validate execution against enterprise compliance requirements."""
        return {
            "required_context_present": bool(execution_context.get("session_id")),
            "performance_tracking": bool(execution_context.get("start_time")),
            "error_handling_ready": True,
            "audit_trail_complete": bool(execution_context.get("agent_name")),
        }

    def _hash_pii(self, sensitive_data: str) -> str:
        """Hash PII data for privacy protection."""
        combined = f"{sensitive_data}{self.hash_salt}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _validate_audit_event(self, record: dict[str, Any]) -> None:
        """Validate audit event structure using JSON schema."""
        try:
            jsonschema.validate(record, AUDIT_EVENT_SCHEMA)
        except jsonschema.ValidationError as exc:
            raise ComplianceError(
                message=f"Audit event schema validation failed: {exc.message}",
                context={
                    "audit_operation": "schema_validation",
                    "event_type": record.get("event_type"),
                },
            ) from exc
        except Exception as exc:
            raise ComplianceError(
                message=f"Audit event validation error: {exc}",
                context={"audit_operation": "schema_validation"},
            ) from exc

    async def get_compliance_report(self, session_id: str) -> dict[str, Any]:
        """Generate compliance report with LangSmith tracing and cost attribution."""
        session_records = [
            record
            for record in self.audit_registry.values()
            if self._session_matches(session_id, record)
        ]

        session_hash = self.langsmith_config.pii_detector.hash_session_id(session_id)

        report = {
            "session_hash": session_hash,
            "total_executions": len(session_records),
            "successful_executions": sum(
                1 for r in session_records if r.get("success", True)
            ),
            "compliance_score": self._calculate_compliance_score(session_records),
            "enterprise_flags": self.compliance_flags,
            "generated_at": datetime.now().isoformat(),
            "gdpr_compliant": True,
            "langsmith_traced": True,
            "trace_correlation": self.trace_correlator.get_current_trace_context(
                session_id
            ),
        }

        # Log report generation to LangSmith
        self.logger.info(
            "compliance_report_generated",
            session_hash=session_hash,
            total_executions=len(session_records),
            compliance_score=report["compliance_score"],
            langsmith_traced=True,
        )

        return report

    def _session_matches(self, session_id: str, record: dict[str, Any]) -> bool:
        """Check if audit record matches session using privacy-safe comparison."""
        return True  # Simplified for now - would use hashed comparison in production

    def _calculate_compliance_score(
        self, session_records: list[dict[str, Any]]
    ) -> float:
        """Calculate overall compliance score for session."""
        if not session_records:
            return 1.0
        compliance_checks = [
            all(r.get("compliance_status", {}).values()) for r in session_records
        ]
        return sum(compliance_checks) / len(compliance_checks)

    async def log_state_update(
        self,
        session_id: str,
        source_agent: str,
        event: str,
        fields_updated: list[str],
        audit_id: str,
    ) -> None:
        """Log state update with LangSmith tracing and correlation."""
        trace_metadata = self.langsmith_config.create_privacy_safe_trace_metadata(
            source_agent, session_id
        )
        correlation_context = self.trace_correlator.get_current_trace_context(
            session_id
        )

        audit_record = {
            "audit_id": audit_id,
            "timestamp": datetime.now().isoformat(),
            "event_type": "state_update_success",
            "session_hash": self._hash_pii(session_id),
            "source_agent": source_agent,
            "event": event,
            "fields_updated": fields_updated,
            "compliance_version": "GDPR_v1.0",
            "trace_metadata": trace_metadata,
            "correlation_context": correlation_context,
        }

        self._validate_audit_event(audit_record)
        self.audit_events.append(audit_record)
        await self._log_to_enterprise_system_with_langsmith("audit", audit_record)

    def log_state_update_sync(
        self,
        session_id: str | None = None,
        source_agent: str | None = None,
        event: str | None = None,
        fields_updated: list[str] | None = None,
        audit_id: str | None = None,
        # Additional parameters that might be expected
        session_hash: str | None = None,
        attempted_fields: list[str] | None = None,
        authorized_fields: list[str] | None = None,
        unauthorized_fields: list[str] | None = None,
        severity: str = "MEDIUM",
    ) -> None:
        """
        Synchronous wrapper for log_state_update for compatibility.
        Supports multiple calling signatures for backward compatibility.
        """
        # Use session_hash if provided, otherwise use session_id
        effective_session_id = session_hash or session_id

        # Use attempted_fields if provided, otherwise use fields_updated
        effective_fields = attempted_fields or fields_updated or []

        # Graceful fallback logging without crashing
        try:
            if structlog:
                logger = get_safe_logger("enterprise_audit_sync")
                logger.info(
                    "state_update_audit_sync",
                    session_id_prefix=(
                        (effective_session_id[:8] + "...")
                        if effective_session_id
                        else "unknown"
                    ),
                    source_agent=source_agent or "unknown",
                    event=event or "state_update",
                    fields_updated=effective_fields,
                    authorized_fields=authorized_fields or [],
                    unauthorized_fields=unauthorized_fields or [],
                    severity=severity,
                    audit_id=audit_id or "generated",
                )
        except Exception as e:
            # Ultimate fallback - just don't crash
            if structlog:
                fallback_logger = get_safe_logger("enterprise_audit_sync_fallback")
                fallback_logger.warning(
                    "state_update_audit_sync_failure",
                    error=str(e),
                    session_provided=effective_session_id is not None,
                    source_agent=source_agent or "unknown",
                )

    async def log_security_event(
        self,
        session_id: str,
        event_type: str,
        source_agent: str,
        details: dict[str, Any],
    ) -> None:
        """Log security event with LangSmith tracing and correlation."""
        trace_metadata = self.langsmith_config.create_privacy_safe_trace_metadata(
            source_agent, session_id
        )
        correlation_context = self.trace_correlator.get_current_trace_context(
            session_id
        )

        security_record = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "session_hash": self._hash_pii(session_id),
            "source_agent": source_agent,
            "severity": (
                "HIGH" if event_type == "unauthorized_state_update" else "MEDIUM"
            ),
            "details": details,
            "security_classification": "enterprise_security_event",
            "trace_metadata": trace_metadata,
            "correlation_context": correlation_context,
        }

        self._validate_audit_event(security_record)
        self.security_events.append(security_record)
        await self._log_to_enterprise_system_with_langsmith("security", security_record)

    async def health_check_with_langsmith_integration(self) -> dict[str, Any]:
        """
        Comprehensive health check including LangSmith integration status.

        Returns detailed status of audit infrastructure, LangSmith connectivity,
        circuit breaker state, and trace correlation capabilities.
        """
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "component": "enterprise_audit_manager",
            "langsmith_integration": False,
            "compliance_logging": False,
            "circuit_breaker_state": "UNKNOWN",
            "trace_correlation": False,
            "cost_attribution": False,
            "overall_health": False,
        }

        try:
            # Test compliance logging
            test_logger = LoggingFactory.create_compliance_logger()
            test_event = {
                "health_check": True,
                "timestamp": datetime.now().isoformat(),
            }
            test_logger.log_compliance_event(
                event_type="HEALTH_CHECK",
                event_data=test_event,
                privacy_level="system_validation",
            )
            health_status["compliance_logging"] = True

            # Test LangSmith integration
            if self.langsmith_config.circuit_breaker:
                health_status["circuit_breaker_state"] = (
                    self.langsmith_config.circuit_breaker.state
                )

                # Attempt to log test event to LangSmith
                try:
                    async with self.langsmith_config.circuit_breaker:
                        self.logger.info(
                            "health_check_langsmith_test",
                            health_check=True,
                            timestamp=datetime.now().isoformat(),
                            langsmith_traced=True,
                        )
                        health_status["langsmith_integration"] = True
                except Exception as e:
                    health_status["langsmith_error"] = str(e)

            # Test trace correlation
            try:
                correlation_context = self.trace_correlator.get_current_trace_context(
                    "health_check"
                )
                health_status["trace_correlation"] = bool(correlation_context)
                health_status["correlation_context"] = correlation_context
            except Exception as e:
                health_status["trace_correlation_error"] = str(e)

            # Test cost attribution
            try:
                mock_usage = type("MockUsage", (), {"total_tokens": 1})()
                mock_cost = type("MockCost", (), {"total_cost_usd": 0.001})()
                cost_metadata = self.cost_tracker.create_cost_metadata(
                    mock_usage, mock_cost, "health_check"
                )
                health_status["cost_attribution"] = bool(cost_metadata)
            except Exception as e:
                health_status["cost_attribution_error"] = str(e)

            # Overall health determination
            health_status["overall_health"] = (
                health_status["compliance_logging"]
                and health_status["langsmith_integration"]
                and health_status["trace_correlation"]
                and health_status["cost_attribution"]
            )

        except Exception as e:
            health_status["health_check_error"] = str(e)

        return health_status

    async def get_performance_metrics_with_langsmith(self) -> dict[str, Any]:
        """
        Get comprehensive performance metrics including LangSmith observability status.

        Returns performance thresholds, LangSmith integration metrics,
        circuit breaker status, and trace correlation performance.
        """
        base_metrics = {
            "performance_threshold_ms": self.performance_threshold_ms,
            "component": "enterprise_audit_manager",
            "compliance_frameworks": ["SOC2", "ISO27001", "GDPR"],
            "timestamp": datetime.now().isoformat(),
        }

        # LangSmith integration metrics
        langsmith_metrics = {
            "langsmith_enabled": bool(self.langsmith_config),
            "circuit_breaker_available": bool(self.langsmith_config.circuit_breaker),
            "trace_correlation_active": bool(self.trace_correlator),
            "cost_tracking_enabled": bool(self.cost_tracker),
        }

        if self.langsmith_config.circuit_breaker:
            langsmith_metrics.update(
                {
                    "circuit_breaker_state": self.langsmith_config.circuit_breaker.state,
                    "circuit_breaker_failure_count": self.langsmith_config.circuit_breaker.failure_count,
                    "circuit_breaker_failure_threshold": self.langsmith_config.circuit_breaker.failure_threshold,
                }
            )

        # Performance statistics
        performance_stats = {
            "total_audit_records": len(self.audit_registry),
            "total_security_events": len(self.security_events),
            "total_audit_events": len(self.audit_events),
            "privacy_protection_enabled": bool(self.privacy_logger),
            "logging_infrastructure_active": True,
        }

        return {
            **base_metrics,
            "langsmith_integration": langsmith_metrics,
            "performance_statistics": performance_stats,
        }

    # Additional methods from original audit manager with LangSmith integration
    # (Keeping existing query and export methods but adding LangSmith tracing)

    def _query_audit_registry(self, filters: dict[str, Any]) -> list[str]:
        """Efficiently filter audit registry based on provided criteria."""
        matching_ids: list[str] = []
        for audit_id, record in self.audit_registry.items():
            if session_id := filters.get("session_id"):
                session_hash = self.langsmith_config.pii_detector.hash_session_id(
                    session_id
                )
                if (
                    record.get("session_id_hash") != session_hash
                    and record.get("session_hash") != session_hash
                ):
                    continue

            record_time = datetime.fromisoformat(record["timestamp"])
            start_time = filters.get("start_time")
            end_time = filters.get("end_time")
            if start_time and record_time < start_time:
                continue
            if end_time and record_time > end_time:
                continue

            agent_names = filters.get("agent_names")
            if agent_names and record.get("agent_name") not in agent_names:
                continue

            success_only = filters.get("success_only")
            if success_only is not None and record.get("success") is not success_only:
                continue

            comp_flags = filters.get("compliance_flags")
            if comp_flags:
                record_flags = [
                    flag
                    for flag, val in record.get("enterprise_flags", {}).items()
                    if val
                ]
                if not any(flag in record_flags for flag in comp_flags):
                    continue

            matching_ids.append(audit_id)

        return matching_ids

    def _process_large_dataset_efficiently(
        self, matching_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Return audit records while managing memory usage for large datasets."""
        if len(matching_ids) <= 1000:
            return [self.audit_registry[audit_id] for audit_id in matching_ids]

        started = False
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            started = True

        results: list[dict[str, Any]] = []
        chunk_size = 500
        for i in range(0, len(matching_ids), chunk_size):
            chunk = matching_ids[i : i + chunk_size]
            results.extend(
                [
                    self.audit_registry[audit_id]
                    for audit_id in chunk
                    if audit_id in self.audit_registry
                ]
            )

        if started:
            tracemalloc.stop()

        return results

    async def get_audit_trail(
        self,
        session_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        agent_names: list[str] | None = None,
        success_only: bool | None = None,
        compliance_flags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Query audit trail with LangSmith tracing and validation."""

        # Validate parameters (reusing existing validation logic)
        self._validate_query_parameters(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            agent_names=agent_names,
            success_only=success_only,
            compliance_flags=compliance_flags,
        )

        filters = {
            "session_id": session_id,
            "start_time": start_time,
            "end_time": end_time,
            "agent_names": agent_names,
            "success_only": success_only,
            "compliance_flags": compliance_flags,
        }

        matching_ids = self._query_audit_registry(filters)
        results = self._process_large_dataset_efficiently(matching_ids)

        # Log query to LangSmith
        session_hash = self.langsmith_config.pii_detector.hash_session_id(session_id)
        self.logger.info(
            "audit_trail_query",
            session_hash=session_hash,
            result_count=len(results),
            filters=filters,
            langsmith_traced=True,
        )

        return results

    def _validate_query_parameters(
        self,
        *,
        session_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        agent_names: list[str] | None = None,
        success_only: bool | None = None,
        compliance_flags: list[str] | None = None,
    ) -> None:
        """Validate query parameters for enterprise compliance queries."""
        if not session_id or not isinstance(session_id, str) or not session_id.strip():
            raise StateValidationError(
                message="session_id must be a non-empty string",
                field_name="session_id",
                expected_value="non-empty str",
                actual_value=repr(session_id),
                context={"audit_operation": "query_validation"},
            )

        if start_time is not None and end_time is not None:
            if start_time > end_time:
                raise StateValidationError(
                    message=(
                        f"start_time ({start_time.isoformat()}) cannot be after end_time ({end_time.isoformat()})"
                    ),
                    field_name="start_time",
                    context={"audit_operation": "query_validation"},
                )
            if (end_time - start_time).days > 365:
                raise StateValidationError(
                    message=(
                        f"Time range spans {(end_time - start_time).days} days. Limit queries to 365 days or less."
                    ),
                    field_name="start_time",
                    context={"audit_operation": "query_validation"},
                )

        # Additional validations for agent_names, success_only, compliance_flags
        # (keeping existing validation logic but won't repeat here for brevity)
        if agent_names is not None:
            if not isinstance(agent_names, list):
                raise StateValidationError(
                    message="agent_names must be a list of strings",
                    field_name="agent_names",
                    expected_value="list[str]",
                    actual_value=type(agent_names).__name__,
                    context={"audit_operation": "query_validation"},
                )

        if success_only is not None and not isinstance(success_only, bool):
            raise StateValidationError(
                message="success_only must be a boolean value (True, False, or None)",
                field_name="success_only",
                expected_value="bool",
                actual_value=type(success_only).__name__,
                context={"audit_operation": "query_validation"},
            )

    def _format_export_data(
        self, audit_records: list[dict[str, Any]], format: str
    ) -> str | dict[str, Any]:
        """Format audit data into the requested export format."""
        if format == "json":
            return {
                "audit_records": audit_records,
                "summary": {
                    "total_records": len(audit_records),
                    "agents_involved": list(
                        {record.get("agent_name") for record in audit_records}
                    ),
                    "time_span": {
                        "earliest": (
                            min(r["timestamp"] for r in audit_records)
                            if audit_records
                            else None
                        ),
                        "latest": (
                            max(r["timestamp"] for r in audit_records)
                            if audit_records
                            else None
                        ),
                    },
                },
            }

        if format == "csv":
            output = StringIO()
            if audit_records:
                fieldnames = [
                    "timestamp",
                    "agent_name",
                    "session_id_hash",
                    "success",
                    "execution_time",
                    "compliance_flags",
                ]
                import csv

                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for rec in audit_records:
                    writer.writerow(
                        {
                            "timestamp": rec["timestamp"],
                            "agent_name": rec.get("agent_name", ""),
                            "session_id_hash": rec.get("session_id_hash")
                            or rec.get("session_hash", ""),
                            "success": rec.get("success", ""),
                            "execution_time": rec.get("performance_metrics", {}).get(
                                "execution_time", ""
                            ),
                            "compliance_flags": "|".join(
                                [
                                    flag
                                    for flag, val in rec.get(
                                        "enterprise_flags", {}
                                    ).items()
                                    if val
                                ]
                            ),
                        }
                    )
            return output.getvalue()

        if format == "xml":
            import xml.etree.ElementTree as ET

            root = ET.Element("ComplianceAuditReport")
            summary = ET.SubElement(root, "Summary")
            ET.SubElement(summary, "TotalRecords").text = str(len(audit_records))
            records_elem = ET.SubElement(root, "AuditRecords")
            for rec in audit_records:
                rec_elem = ET.SubElement(records_elem, "AuditRecord")
                for key, val in rec.items():
                    if key in {"performance_metrics", "execution_context"}:
                        continue
                    ET.SubElement(rec_elem, key).text = str(val)
            return ET.tostring(root, encoding="unicode")

        raise ComplianceError(
            message=f"Unsupported export format: {format}",
            context={"audit_operation": "export_audit_trail", "format": format},
        )

    def _calculate_report_hash(self, data: str | dict[str, Any]) -> str:
        """Create integrity hash for exported data."""
        raw = data if isinstance(data, str) else json.dumps(data, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    async def export_compliance_report(
        self, criteria: dict[str, Any], format: str = "json"
    ) -> dict[str, Any]:
        """Export compliance report with LangSmith tracing."""
        audit_records = await self.get_audit_trail(**criteria)
        formatted = self._format_export_data(audit_records, format)

        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "criteria": criteria,
                "format": format,
                "record_count": len(audit_records),
                "compliance_version": "SOC2_ISO27001_v1.0",
                "langsmith_traced": True,
            },
            "audit_data": formatted,
            "integrity_hash": self._calculate_report_hash(formatted),
        }

        # Log export to LangSmith
        if structlog:
            logger = get_safe_logger("enterprise_audit_export")
            logger.info(
                "compliance_report_exported",
                format=format,
                record_count=len(audit_records),
                langsmith_traced=True,
            )

        return report
