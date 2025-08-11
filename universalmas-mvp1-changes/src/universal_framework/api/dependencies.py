"""API dependencies for session management."""

from __future__ import annotations

from typing import cast

from universal_framework.compliance.audit_manager import EnterpriseAuditManager

# Privacy logging now handled via dependency injection
from universal_framework.compliance.privacy_logger import PrivacySafeLogger
from universal_framework.compliance.safe_mode import SafeModeAuditManager
from universal_framework.config.feature_flags import feature_flags
from universal_framework.config.workflow_config import WorkflowConfig
from universal_framework.contracts.session.interfaces import AuditTrailInterface
from universal_framework.redis.connection import RedisConnectionAdapter
from universal_framework.redis.session_storage import SessionStorage
from universal_framework.session.contract_wrapper import (
    ContractEnterpriseSessionManager,
)
from universal_framework.session.session_manager import EnterpriseSessionManager


def get_feature_flags():
    """Get feature flags instance."""
    return feature_flags


async def initialize_redis_connection() -> None:
    """Initialize Redis connection for API startup."""
    global _redis_adapter
    try:
        config = WorkflowConfig()
        if config.enable_redis_optimization:
            adapter = RedisConnectionAdapter(config)
            await adapter.connect()
            _redis_adapter = adapter
    except Exception:  # noqa: BLE001
        pass


_redis_adapter: RedisConnectionAdapter | None = None
_session_manager: EnterpriseSessionManager | None = None
_session_storage: SessionStorage | None = None
_contract_session_manager: ContractEnterpriseSessionManager | None = None


def _create_safe_mode_audit_manager(
    privacy_logger: PrivacySafeLogger,
) -> AuditTrailInterface:
    """Create a minimal audit manager for safe mode that implements the interface without enterprise features."""
    return cast(AuditTrailInterface, SafeModeAuditManager())


def get_session_manager() -> ContractEnterpriseSessionManager:
    """Get session manager with conditional enterprise features based on safe mode."""
    global _session_manager, _contract_session_manager
    if _session_manager is None:
        privacy_logger = PrivacySafeLogger()

        # Conditionally create audit manager based on feature flags
        if feature_flags.is_enabled("ENTERPRISE_AUDIT_VALIDATION"):
            from ..observability.enterprise_langsmith import EnterpriseLangSmithConfig

            langsmith_config = EnterpriseLangSmithConfig()
            audit = cast(
                AuditTrailInterface,
                EnterpriseAuditManager(privacy_logger, langsmith_config),
            )
        else:
            # Safe mode: Use minimal audit implementation
            audit = _create_safe_mode_audit_manager(privacy_logger)

        _session_manager = EnterpriseSessionManager(_redis_adapter, audit)
    if _contract_session_manager is None:
        _contract_session_manager = ContractEnterpriseSessionManager(_session_manager)
    return _contract_session_manager


def get_redis_adapter() -> RedisConnectionAdapter | None:
    """Return initialized Redis adapter if available."""
    return _redis_adapter


def get_session_storage() -> SessionStorage:
    """Return SessionStorage instance backed by Redis."""
    global _session_storage
    adapter = get_redis_adapter()
    if _session_storage is None or _session_storage.redis_adapter is not adapter:
        _session_storage = SessionStorage(adapter)
    return _session_storage
