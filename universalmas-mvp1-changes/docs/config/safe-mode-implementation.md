# Safe Mode Implementation Guide

This guide provides technical details for developers implementing and extending the safe mode system.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
├─────────────────────────────────────────────────────────────┤
│  Feature Flags System (TemporaryFeatureFlags)              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐  │
│  │ Environment     │ │ Runtime Config  │ │ Safe Mode    │  │
│  │ Variables       │ │ Loading         │ │ Detection    │  │
│  └─────────────────┘ └─────────────────┘ └──────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Conditional Middleware Loading                             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐  │
│  │ Enterprise Auth │ │ LangSmith       │ │ Compliance   │  │
│  │ Middleware      │ │ Tracing         │ │ Validation   │  │
│  │ [Conditional]   │ │ [Conditional]   │ │ [Conditional]│  │
│  └─────────────────┘ └─────────────────┘ └──────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Safe Fallback Implementations                             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐  │
│  │ SafeAuditMgr    │ │ SafePrivacy     │ │ SafeAuthz    │  │
│  │ (No-op logging) │ │ (No redaction)  │ │ (Allow all)  │  │
│  └─────────────────┘ └─────────────────┘ └──────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Core Framework (Always Available)                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐  │
│  │ Workflow        │ │ Session         │ │ Health       │  │
│  │ Execution       │ │ Management      │ │ Endpoints    │  │
│  └─────────────────┘ └─────────────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Feature Flag System Implementation

### Core Interface

```python
class TemporaryFeatureFlags:
    """Feature flags for safe mode operation during development/debugging."""
    
    def __init__(self):
        self.core_features = {
            "WORKFLOW_EXECUTION": True,
            "SESSION_MANAGEMENT": True,
            "HEALTH_ENDPOINTS": True,
            "BASIC_LOGGING": True,
        }
        
        self.enterprise_features = {
            "ENTERPRISE_FEATURES": self._get_env_bool("ENTERPRISE_FEATURES", False),
            "ENTERPRISE_AUTH_MIDDLEWARE": self._get_env_bool("ENTERPRISE_AUTH_MIDDLEWARE", False),
            "ENTERPRISE_AUDIT_VALIDATION": self._get_env_bool("ENTERPRISE_AUDIT_VALIDATION", False),
            "LANGSMITH_TRACING": self._get_env_bool("LANGSMITH_TRACING", False),
            "PII_REDACTION": self._get_env_bool("PII_REDACTION", False),
            "AUTHORIZATION_MATRIX": self._get_env_bool("AUTHORIZATION_MATRIX", False),
            "COMPLIANCE_MONITORING": self._get_env_bool("COMPLIANCE_MONITORING", False),
        }
```

### Environment Variable Resolution

```python
def _get_env_bool(self, key: str, default: bool) -> bool:
    """Get boolean environment variable with safe mode override."""
    value = os.getenv(key, str(default)).lower()
    
    # Safe mode overrides enterprise features to false
    if self._is_safe_mode_active() and key in self.enterprise_features:
        return False
        
    return value in ('true', '1', 'yes', 'on')

def _is_safe_mode_active(self) -> bool:
    """Check if safe mode is explicitly enabled."""
    return os.getenv("SAFE_MODE", "true").lower() in ('true', '1', 'yes', 'on')
```

## Safe Fallback Implementation Patterns

### No-Op Pattern (Audit Manager)

```python
class SafeEnterpriseAuditManager:
    """Safe fallback with logging but no validation failures."""
    
    def __init__(self, privacy_logger: Any = None, langsmith_config: Any = None, hash_salt: str | None = None):
        self.logger = structlog.get_logger("safe_mode_audit")
        
    async def log_state_update(self, *args: Any, **kwargs: Any) -> None:
        """Log call but don't perform complex validation."""
        self.logger.debug("safe_mode_log_state_update_called", args=args, kwargs=kwargs)
        # No-op: just log that it was called, don't crash
        
    async def log_operation(self, operation: str, session_id: str, metadata: dict[str, Any]) -> str:
        """Return audit ID without storing to external systems."""
        audit_id = f"safe_audit_{uuid4()}"
        self.logger.info("safe_mode_operation_logged", 
                        operation=operation, 
                        session_id_prefix=session_id[:8] + "...",
                        audit_id=audit_id)
        return audit_id
```

### Pass-Through Pattern (Privacy Logger)

```python
class SafePrivacySafeLogger:
    """Safe fallback that bypasses PII redaction with warnings."""
    
    def redact_pii(self, text: str) -> str:
        """Pass through without redaction in safe mode."""
        self.logger.debug("safe_mode_pii_redaction_bypassed")
        return text  # No redaction, just return original
        
    def log_session_event(self, *args: Any, **kwargs: Any) -> None:
        """Basic logging without privacy filtering."""
        self.logger.info("safe_mode_session_event", args=args, kwargs=kwargs)
```

### Allow-All Pattern (Authorization Matrix)

```python
class SafeAuthorizationMatrix:
    """Safe authorization that allows all operations."""
    
    @classmethod
    def get_authorized_fields(cls, agent_name: str) -> set[str]:
        """Safe mode: allow all fields for all agents."""
        return {
            "message_history", "can_advance", "email_requirements", 
            "current_node", "last_update_timestamp", "user_objective",
            # ... all possible fields
        }
    
    @classmethod  
    def validate_agent_authorization(cls, agent_name: str, attempted_fields: set[str]) -> tuple[bool, set[str], set[str]]:
        """Safe mode: authorize all operations."""
        authorized_fields = cls.get_authorized_fields(agent_name)
        return True, authorized_fields, set()  # Authorize everything
```

## Conditional Middleware Loading

### FastAPI Middleware Pattern

```python
def create_safe_mode_app() -> FastAPI:
    """Create FastAPI app with conditional middleware."""
    
    app = FastAPI(
        title="Universal Multi-Agent System Framework" + 
              (" [SAFE MODE]" if flags.is_safe_mode() else ""),
        version="0.1.0"
    )
    
    # Core middleware (always loaded)
    app.add_middleware(CORSMiddleware, allow_origins=["*"])
    
    # Enterprise middleware (conditional)
    if flags.is_enabled("ENTERPRISE_AUTH_MIDDLEWARE"):
        try:
            from universal_framework.api.middleware import EnterpriseAuthMiddleware
            app.add_middleware(EnterpriseAuthMiddleware)
        except ImportError as e:
            logger.warning("Enterprise auth middleware unavailable", error=str(e))
    
    if flags.is_enabled("LANGSMITH_TRACING"):
        try:
            from universal_framework.observability.langsmith_middleware import LangSmithAPITracingMiddleware
            app.add_middleware(LangSmithAPITracingMiddleware)
        except ImportError as e:
            logger.warning("LangSmith middleware unavailable", error=str(e))
    
    return app
```

## Monkey Patching for Safe Mode

### Runtime Component Replacement

```python
def apply_safe_mode_patches():
    """Replace enterprise components with safe fallbacks."""
    if not flags.is_safe_mode():
        return
        
    import sys
    
    # Replace audit manager
    if 'universal_framework.compliance.audit_manager' in sys.modules:
        sys.modules['universal_framework.compliance.audit_manager'].EnterpriseAuditManager = SafeEnterpriseAuditManager
    
    # Replace privacy logger  
    if 'universal_framework.compliance.privacy_logger' in sys.modules:
        sys.modules['universal_framework.compliance.privacy_logger'].PrivacySafeLogger = SafePrivacySafeLogger
        
    # Replace authorization matrix
    if 'universal_framework.compliance.authorization_matrix' in sys.modules:
        sys.modules['universal_framework.compliance.authorization_matrix'].AuthorizationMatrix = SafeAuthorizationMatrix
```

## Async/Sync Boundary Handling

### Sync Wrapper Pattern

```python
def log_state_update_sync(self, session_id: str, source_agent: str, event: str, fields_updated: list[str], audit_id: str) -> None:
    """Synchronous wrapper for async log_state_update."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule as task if loop is running
            asyncio.create_task(
                self.log_state_update(session_id, source_agent, event, fields_updated, audit_id)
            )
        else:
            # Run directly if no loop
            loop.run_until_complete(
                self.log_state_update(session_id, source_agent, event, fields_updated, audit_id)
            )
    except Exception as e:
        # Graceful fallback
        logger.warning("Could not execute async log_state_update", error=str(e))
```

## Testing Safe Mode Components

### Unit Test Pattern

```python
class TestSafeModeComponents:
    """Test safe mode fallback implementations."""
    
    def test_safe_audit_manager_no_op(self):
        """Verify safe audit manager doesn't raise exceptions."""
        manager = SafeEnterpriseAuditManager()
        
        # Should not raise any exceptions
        result = asyncio.run(manager.log_state_update("session", "agent", "event", ["field"], "audit_id"))
        assert result is None  # No-op returns None
        
    def test_safe_privacy_logger_pass_through(self):
        """Verify safe privacy logger passes through text unchanged."""
        logger = SafePrivacySafeLogger()
        
        sensitive_text = "SSN: 123-45-6789"
        result = logger.redact_pii(sensitive_text)
        assert result == sensitive_text  # No redaction in safe mode
        
    def test_safe_authorization_allows_all(self):
        """Verify safe authorization allows all operations."""
        allowed, authorized, unauthorized = SafeAuthorizationMatrix.validate_agent_authorization(
            "test_agent", {"restricted_field", "public_field"}
        )
        
        assert allowed is True
        assert len(unauthorized) == 0  # No unauthorized fields
```

### Integration Test Pattern

```python
class TestSafeModeIntegration:
    """Test safe mode with full application stack."""
    
    def test_app_starts_in_safe_mode(self):
        """Verify application starts successfully in safe mode."""
        os.environ['SAFE_MODE'] = 'true'
        os.environ['ENTERPRISE_FEATURES'] = 'false'
        
        app = create_safe_mode_app()
        assert app is not None
        
        # Verify safe mode endpoints
        with TestClient(app) as client:
            response = client.get("/safe-mode-status")
            assert response.status_code == 200
            assert response.json()["feature_flags"]["safe_mode"] is True
```

## Extension Guidelines

### Adding New Enterprise Features

1. **Add to Feature Flags**:
```python
self.enterprise_features = {
    # existing features...
    "NEW_ENTERPRISE_FEATURE": self._get_env_bool("NEW_ENTERPRISE_FEATURE", False),
}
```

2. **Create Safe Fallback**:
```python
class SafeNewEnterpriseComponent:
    """Safe fallback for new enterprise component."""
    
    def enterprise_method(self, *args, **kwargs):
        logger.debug("safe_mode_new_feature_bypassed")
        return default_safe_value
```

3. **Add Conditional Loading**:
```python
if flags.is_enabled("NEW_ENTERPRISE_FEATURE"):
    # Load real implementation
    pass
```

4. **Update Documentation**:
- Add environment variable to config table
- Document safe mode behavior
- Add troubleshooting notes

### Safe Mode Design Principles

1. **Fail Safe**: Safe mode should never crash the application
2. **Visible**: Log all safe mode operations for debugging
3. **Predictable**: Safe mode behavior should be deterministic
4. **Reversible**: Easy to switch back to full functionality
5. **Testable**: All safe mode paths should be unit tested

---

This implementation guide ensures consistent patterns across all safe mode components and provides clear extension points for future enterprise features.
