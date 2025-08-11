# Production Fixes Implementation Plan

## Overview

This plan addresses the production gaps identified in the architecture compliance review, focusing on configuration validation, error recovery standardization, and monitoring integration.

## Phase 1: Configuration Validation (Priority: HIGH)

### 1.1 Production Configuration Schema
**File**: `config/production.toml`
**Status**: NEW

```toml
[environment]
name = "production"
debug = false
log_level = "INFO"
safe_mode = false

[redis]
url = "${REDIS_URL}"
max_connections = 50
connection_timeout = 5
health_check_interval = 30
retry_attempts = 3
retry_delay = 1

[security]
rate_limit_requests = 100
rate_limit_window = 60
session_timeout_hours = 24
max_session_age_hours = 168
pii_detection = true

[monitoring]
datadog_enabled = true
metrics_interval = 60
health_check_endpoint = "/health"
performance_logging = true
error_rate_threshold = 0.05

[llm]
provider = "openai"
timeout = 30
max_retries = 3
model = "gpt-4"
temperature = 0.7

[compliance]
audit_retention_days = 90
gdpr_compliance = true
soc2_compliance = true
fail_closed_validation = true
```

### 1.2 Configuration Validator
**File**: `src/universal_framework/config/production_validator.py`
**Status**: NEW

```python
"""Production configuration validation service."""

import os
import tomllib
from pathlib import Path
from typing import Any, Dict, List

import redis.asyncio as redis
import structlog
from pydantic import BaseModel, Field, validator

from universal_framework.llm.providers import LLMConfig

logger = structlog.get_logger("config_validator")


class RedisConfig(BaseModel):
    """Redis configuration validation."""
    url: str = Field(..., description="Redis connection URL")
    max_connections: int = Field(50, ge=1, le=100)
    connection_timeout: int = Field(5, ge=1, le=30)
    health_check_interval: int = Field(30, ge=5, le=300)
    retry_attempts: int = Field(3, ge=1, le=10)
    retry_delay: int = Field(1, ge=0, le=60)


class SecurityConfig(BaseModel):
    """Security configuration validation."""
    rate_limit_requests: int = Field(100, ge=1, le=1000)
    rate_limit_window: int = Field(60, ge=1, le=3600)
    session_timeout_hours: int = Field(24, ge=1, le=168)
    max_session_age_hours: int = Field(168, ge=1, le=720)
    pii_detection: bool = True


class MonitoringConfig(BaseModel):
    """Monitoring configuration validation."""
    datadog_enabled: bool = False
    metrics_interval: int = Field(60, ge=10, le=3600)
    health_check_endpoint: str = "/health"
    performance_logging: bool = True
    error_rate_threshold: float = Field(0.05, ge=0.0, le=1.0)


class ProductionConfig(BaseModel):
    """Complete production configuration."""
    environment: str = Field("production", regex="^(production|staging)$")
    debug: bool = False
    log_level: str = Field("INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    safe_mode: bool = False
    
    redis: RedisConfig
    security: SecurityConfig
    monitoring: MonitoringConfig
    
    @validator('redis')
    def validate_redis_url(cls, v):
        if not v.url.startswith(('redis://', 'rediss://')):
            raise ValueError("Redis URL must start with redis:// or rediss://")
        return v


class ProductionConfigValidator:
    """Production configuration validation service."""
    
    def __init__(self, config_path: str = "config/production.toml"):
        self.config_path = Path(config_path)
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
    
    async def validate_configuration(self) -> Dict[str, Any]:
        """Validate complete production configuration."""
        self.validation_errors.clear()
        self.validation_warnings.clear()
        
        # Load configuration
        config_data = self._load_configuration()
        
        # Validate schema
        try:
            config = ProductionConfig(**config_data)
        except Exception as e:
            self.validation_errors.append(f"Configuration validation failed: {e}")
            return self._get_validation_result()
        
        # Validate external dependencies
        await self._validate_redis_connection(config.redis)
        await self._validate_llm_configuration()
        
        return self._get_validation_result()
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load and merge configuration from all sources."""
        config_data = {}
        
        # Load from TOML file
        if self.config_path.exists():
            with open(self.config_path, "rb") as f:
                config_data = tomllib.load(f)
        
        # Override with environment variables
        config_data.update(self._get_env_overrides())
        
        return config_data
    
    def _get_env_overrides(self) -> Dict[str, Any]:
        """Get environment variable overrides."""
        overrides = {}
        
        # Redis
        if redis_url := os.getenv("REDIS_URL"):
            overrides.setdefault("redis", {})["url"] = redis_url
        
        # LLM
        if openai_key := os.getenv("OPENAI_API_KEY"):
            overrides.setdefault("llm", {})["api_key"] = openai_key
        
        return overrides
    
    async def _validate_redis_connection(self, redis_config: RedisConfig) -> bool:
        """Validate Redis connectivity."""
        try:
            client = redis.from_url(
                redis_config.url,
                max_connections=redis_config.max_connections,
                socket_connect_timeout=redis_config.connection_timeout,
                socket_timeout=redis_config.connection_timeout,
            )
            await client.ping()
            await client.close()
            logger.info("Redis connection validated successfully")
            return True
        except Exception as e:
            self.validation_errors.append(f"Redis connection failed: {e}")
            return False
    
    async def _validate_llm_configuration(self) -> bool:
        """Validate LLM provider configuration."""
        try:
            config = LLMConfig.from_env()
            # Basic validation - could be enhanced with actual connectivity test
            if not config.api_key:
                self.validation_errors.append("LLM API key not configured")
                return False
            logger.info("LLM configuration validated successfully")
            return True
        except Exception as e:
            self.validation_errors.append(f"LLM configuration validation failed: {e}")
            return False
    
    def _get_validation_result(self) -> Dict[str, Any]:
        """Get validation result with recommendations."""
        return {
            "valid": len(self.validation_errors) == 0,
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "recommendations": self._get_recommendations()
        }
    
    def _get_recommendations(self) -> List[str]:
        """Get configuration recommendations."""
        recommendations = []
        
        if not self.config_path.exists():
            recommendations.append(
                f"Create production configuration file: {self.config_path}"
            )
        
        if not os.getenv("REDIS_URL"):
            recommendations.append(
                "Set REDIS_URL environment variable for production Redis"
            )
        
        if not os.getenv("OPENAI_API_KEY"):
            recommendations.append(
                "Set OPENAI_API_KEY environment variable for LLM provider"
            )
        
        return recommendations
```

## Phase 2: Error Recovery Standardization (Priority: HIGH)

### 2.1 Production Error Recovery Service
**File**: `src/universal_framework/workflow/production_error_recovery.py`
**Status**: NEW

```python
"""Production-grade error recovery with circuit breakers and graceful degradation."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import structlog
from universal_framework.contracts.state import UniversalWorkflowState

logger = structlog.get_logger("production_error_recovery")


class CircuitBreakerState:
    """Circuit breaker state management."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def should_allow_request(self) -> bool:
        """Check if request should be allowed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self.last_failure_time and time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False
    
    def record_success(self) -> None:
        """Record successful request."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self) -> None:
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class ProductionErrorRecovery:
    """Production-grade error recovery service."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.fallback_strategies = {
            "requirements_agent": self._fallback_requirements,
            "strategy_generator": self._fallback_strategy,
            "confirmation_agent": self._fallback_confirmation,
            "email_generator": self._fallback_email,
        }
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "circuit_breaker_activations": 0,
            "fallback_activations": 0,
        }
    
    def get_circuit_breaker(self, agent_name: str) -> CircuitBreakerState:
        """Get or create circuit breaker for agent."""
        if agent_name not in self.circuit_breakers:
            self.circuit_breakers[agent_name] = CircuitBreakerState(
                failure_threshold=self.config.get("circuit_breaker_threshold", 5),
                timeout=self.config.get("circuit_breaker_timeout", 60)
            )
        return self.circuit_breakers[agent_name]
    
    async def execute_with_recovery(
        self,
        agent_name: str,
        agent_func: Callable,
        state: UniversalWorkflowState,
        timeout: Optional[int] = None
    ) -> UniversalWorkflowState:
        """Execute agent with production error recovery."""
        self.metrics["total_executions"] += 1
        timeout = timeout or self.config.get("agent_timeout", 30)
        
        circuit_breaker = self.get_circuit_breaker(agent_name)
        
        # Check circuit breaker
        if not circuit_breaker.should_allow_request():
            self.metrics["circuit_breaker_activations"] += 1
            logger.warning(
                "Circuit breaker activated",
                agent=agent_name,
                state=circuit_breaker.state
            )
            return await self._execute_fallback(agent_name, state)
        
        try:
            # Execute with timeout
            start_time = time.time()
            
            if asyncio.iscoroutinefunction(agent_func):
                result = await asyncio.wait_for(
                    agent_func(state),
                    timeout=timeout
                )
            else:
                # Handle sync functions
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, agent_func, state
                    ),
                    timeout=timeout
                )
            
            execution_time = time.time() - start_time
            circuit_breaker.record_success()
            self.metrics["successful_executions"] += 1
            
            # Add performance metadata
            return self._add_performance_metadata(result, agent_name, execution_time)
            
        except asyncio.TimeoutError:
            circuit_breaker.record_failure()
            self.metrics["failed_executions"] += 1
            logger.error(
                "Agent execution timeout",
                agent=agent_name,
                timeout=timeout
            )
            return await self._create_error_state(
                state, agent_name, "timeout", f"Execution timeout after {timeout}s"
            )
            
        except Exception as e:
            circuit_breaker.record_failure()
            self.metrics["failed_executions"] += 1
            logger.error(
                "Agent execution failed",
                agent=agent_name,
                error=str(e),
                exc_info=True
            )
            return await self._create_error_state(
                state, agent_name, "execution_error", str(e)
            )
    
    async def _execute_fallback(
        self, agent_name: str, state: UniversalWorkflowState
    ) -> UniversalWorkflowState:
        """Execute fallback strategy for agent."""
        self.metrics["fallback_activations"] += 1
        
        fallback_func = self.fallback_strategies.get(agent_name)
        if fallback_func:
            logger.info("Executing fallback strategy", agent=agent_name)
            return await fallback_func(state)
        
        # Return state with error if no fallback available
        return await self._create_error_state(
            state, agent_name, "no_fallback", "No fallback strategy available"
        )
    
    def _add_performance_metadata(
        self, state: UniversalWorkflowState, agent_name: str, execution_time: float
    ) -> UniversalWorkflowState:
        """Add performance metadata to state."""
        # Defensive programming for LangGraph state conversion
        context_data = state.context_data if hasattr(state, 'context_data') else state.get('context_data', {})
        performance_data = context_data.get('performance', {})
        
        performance_data[agent_name] = {
            'execution_time': execution_time,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'success'
        }
        
        return state.copy(
            update={
                'context_data': {
                    **context_data,
                    'performance': performance_data
                }
            }
        )
    
    async def _create_error_state(
        self, 
        state: UniversalWorkflowState, 
        agent_name: str, 
        error_type: str, 
        error_message: str
    ) -> UniversalWorkflowState:
        """Create error state with recovery information."""
        # Defensive programming for LangGraph state conversion
        error_recovery_state = state.error_recovery_state if hasattr(state, 'error_recovery_state') else state.get('error_recovery_state', {})
        recovery_attempts = state.recovery_attempts if hasattr(state, 'recovery_attempts') else state.get('recovery_attempts', {})
        context_data = state.context_data if hasattr(state, 'context_data') else state.get('context_data', {})
        
        error_info = {
            'agent_name': agent_name,
            'error_type': error_type,
            'error_message': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            'recovery_suggested': True
        }
        
        return state.copy(
            update={
                'error_recovery_state': {
                    **error_recovery_state,
                    agent_name: error_info
                },
                'recovery_attempts': {
                    **recovery_attempts,
                    agent_name: recovery_attempts.get(agent_name, 0) + 1
                },
                'context_data': {
                    **context_data,
                    'last_error': error_info,
                    'agent_execution_failed': True
                }
            }
        )
    
    # Fallback strategies
    async def _fallback_requirements(self, state: UniversalWorkflowState) -> UniversalWorkflowState:
        """Fallback requirements collection using simulation."""
        from universal_framework.workflow.nodes import batch_requirements_collector
        return await batch_requirements_collector(state)
    
    async def _fallback_strategy(self, state: UniversalWorkflowState) -> UniversalWorkflowState:
        """Fallback strategy generation using simulation."""
        from universal_framework.workflow.nodes import strategy_generator
        return await strategy_generator(state)
    
    async def _fallback_confirmation(self, state: UniversalWorkflowState) -> UniversalWorkflowState:
        """Fallback strategy confirmation using simulation."""
        from universal_framework.workflow.nodes import strategy_confirmation_handler
        return await strategy_confirmation_handler(state)
    
    async def _fallback_email(self, state: UniversalWorkflowState) -> UniversalWorkflowState:
        """Fallback email generation using simulation."""
        from universal_framework.workflow.nodes import enhanced_email_generator
        return await enhanced_email_generator(state)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get error recovery metrics."""
        return {
            **self.metrics,
            'circuit_breakers': {
                name: {
                    'state': cb.state,
                    'failure_count': cb.failure_count,
                    'last_failure': cb.last_failure_time
                }
                for name, cb in self.circuit_breakers.items()
            }
        }
```

## Phase 3: Monitoring Integration (Priority: MEDIUM)

### 3.1 Production Monitoring Service
**File**: `src/universal_framework/observability/production_monitoring.py`
**Status**: NEW

```python
"""Production monitoring integration with Datadog and enterprise metrics."""

import time
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger("production_monitoring")


class ProductionMonitor:
    """Production monitoring service."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics_buffer = []
        self.is_enabled = config.get("monitoring", {}).get("enabled", False)
        
    def record_workflow_start(self, session_id: str, user_id: str) -> None:
        """Record workflow start metrics."""
        if not self.is_enabled:
            return
            
        self.metrics_buffer.append({
            'metric': 'workflow.start',
            'session_id': session_id,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def record_agent_execution(
        self, 
        agent_name: str, 
        duration: float, 
        success: bool, 
        error_type: Optional[str] = None
    ) -> None:
        """Record agent execution metrics."""
        if not self.is_enabled:
            return
            
        self.metrics_buffer.append({
            'metric': 'agent.execution',
            'agent_name': agent_name,
            'duration': duration,
            'success': success,
            'error_type': error_type,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def record_workflow_completion(self, session_id: str, duration: float) -> None:
        """Record workflow completion metrics."""
        if not self.is_enabled:
            return
            
        self.metrics_buffer.append({
            'metric': 'workflow.complete',
            'session_id': session_id,
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def flush_metrics(self) -> None:
        """Flush buffered metrics."""
        if not self.is_enabled or not self.metrics_buffer:
            return
            
        # In production, this would send to Datadog or similar
        logger.info("Flushing metrics", metrics_count=len(self.metrics_buffer))
        self.metrics_buffer.clear()
```

## Phase 4: Health Check Endpoints (Priority: MEDIUM)

### 4.1 Health Check Service
**File**: `src/universal_framework/api/routes/health.py`
**Status**: UPDATE

```python
"""Production health check endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from universal_framework.config.production_validator import ProductionConfigValidator
from universal_framework.redis.session_manager import SessionManagerImpl

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with dependency validation."""
    validator = ProductionConfigValidator()
    validation_result = await validator.validate_configuration()
    
    # Check Redis connectivity
    redis_health = await _check_redis_health()
    
    # Check LLM provider
    llm_health = await _check_llm_health()
    
    return {
        "overall_status": "healthy" if validation_result["valid"] else "unhealthy",
        "configuration": validation_result,
        "redis": redis_health,
        "llm": llm_health,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Kubernetes readiness probe."""
    # Check if service is ready to accept traffic
    validator = ProductionConfigValidator()
    validation_result = await validator.validate_configuration()
    
    if not validation_result["valid"]:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Kubernetes liveness probe."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


async def _check_redis_health() -> Dict[str, Any]:
    """Check Redis health."""
    try:
        from universal_framework.redis.connection import RedisConnectionAdapter
        connection = RedisConnectionAdapter()
        is_healthy = await connection.is_healthy()
        return {"status": "healthy" if is_healthy else "unhealthy", "connected": is_healthy}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_llm_health() -> Dict[str, Any]:
    """Check LLM provider health."""
    try:
        from universal_framework.llm.providers import LLMConfig
        config = LLMConfig.from_env()
        return {"status": "healthy", "provider": config.provider}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Phase 2: Observability Standardization (Priority: CRITICAL)

### 2.1 Logging System Inconsistencies Analysis

Based on comprehensive codebase analysis, **13 files** require logging pattern updates to achieve consistency with the enterprise observability architecture.

#### **🚨 HIGH PRIORITY - Legacy `logging.getLogger()` Usage**

These files use the old Python standard library logging instead of the enterprise logging system:

**1. `src/universal_framework/api/response_transformer.py`**
- **Issue**: Uses `import logging` and `logger = logging.getLogger(__name__)`
- **Required Change**: Convert to `UniversalFrameworkLogger("response_transformer")`
- **Impact**: Missing enterprise features (PII redaction, audit trails, structured logging)

**2. `src/universal_framework/utils/state_access.py`**  
- **Issue**: Uses `import logging` and `logger = logging.getLogger(__name__)`
- **Required Change**: Convert to `UniversalFrameworkLogger("state_access")`
- **Impact**: Critical utility missing comprehensive error context

**3. `src/universal_framework/observability/otlp_router.py`**
- **Issue**: Uses `import logging` and `self.logger = logging.getLogger(__name__)`
- **Required Change**: Convert to `UniversalFrameworkLogger("otlp_router")`
- **Impact**: Observability component itself missing enterprise logging

#### **🔄 MEDIUM PRIORITY - Mixed Patterns Needing Standardization**

These files use `structlog.get_logger()` instead of the standardized enterprise logging:

**4. `src/universal_framework/redis/session_storage.py`**
- **Issue**: Uses `self.logger = structlog.get_logger("session_storage")`
- **Required Change**: Convert to `UniversalFrameworkLogger("session_storage")`  
- **Impact**: Missing privacy-safe session handling and enterprise audit features

**5. `src/universal_framework/utils/session_logging.py`**
- **Issue**: Uses `self.logger = structlog.get_logger("session_flow")`
- **Required Change**: Convert to `UniversalFrameworkLogger("session_flow")`
- **Impact**: Session flow logging missing comprehensive context

**6. `src/universal_framework/compliance/safe_mode.py`**
- **Issue**: Uses `self.logger = structlog.get_logger(__name__)`
- **Required Change**: Convert to `UniversalFrameworkLogger("safe_mode")`
- **Impact**: Safe mode operations missing enterprise error handling

#### **⚠️ WORKFLOW FILES - Multiple `structlog.get_logger()` Calls**

These files have multiple instances of direct structlog usage instead of unified logging:

**7. `src/universal_framework/api/routes/workflow.py`**
- **Issues**: 17 instances of `structlog.get_logger()` with different names
- **Examples**: `session_debug`, `conversation_debug`, `intent_debug`, `response_debug`, `workflow`, `workflow_completion`, `workflow_async`
- **Required Change**: Consolidate to single `UniversalFrameworkLogger("workflow_routes")`

**8. `src/universal_framework/agents/intent_classifier.py`**
- **Issues**: 9 instances of `structlog.get_logger("intent_classifier")`
- **Required Change**: Single instance of `UniversalFrameworkLogger("intent_classifier")`

**9. `src/universal_framework/agents/strategy_generator.py`**
- **Issues**: 2 instances of `structlog.get_logger(__name__)` 
- **Required Change**: Convert to `UniversalFrameworkLogger("strategy_generator")`

**10. `src/universal_framework/workflow/orchestrator.py`**
- **Issues**: Uses both `SessionFlowLogger()` and `structlog.get_logger(__name__)`
- **Required Change**: Standardize to `UniversalFrameworkLogger("orchestrator")`

#### **🔧 CONFIG/ENVIRONMENT FILES**

**11. `src/universal_framework/config/environment.py`**
- **Issue**: Uses `logger = structlog.get_logger()`
- **Required Change**: Convert to `UniversalFrameworkLogger("environment")`

**12. `src/universal_framework/config/toml_loader.py`**
- **Issue**: Uses `logger = structlog.get_logger()`
- **Required Change**: Convert to `UniversalFrameworkLogger("toml_loader")`

**13. `src/universal_framework/llm/providers.py`**
- **Issue**: Uses `logger = structlog.get_logger()`
- **Required Change**: Convert to `UniversalFrameworkLogger("llm_providers")`

### 2.2 Standard Import Pattern

**Required Standard Pattern:**
```python
from universal_framework.observability.unified_logger import UniversalFrameworkLogger

logger = UniversalFrameworkLogger("component_name")
```

**Incorrect Import Patterns Found:**
- `import logging` + `logging.getLogger(__name__)` (3 files)
- `structlog.get_logger()` without component name (3 files) 
- `structlog.get_logger(__name__)` (4 files)
- `structlog.get_logger("specific_name")` (multiple instances across files)
- Mixed usage of `SessionFlowLogger()` alongside other patterns

### 2.3 Files Already Using Enterprise Patterns ✅

These files do NOT require changes (already using enterprise patterns):
- ✅ `src/universal_framework/agents/intent_analyzer_chain.py` - Uses `UniversalFrameworkLogger`
- ✅ `src/universal_framework/workflow/intent_classification_nodes.py` - Uses `UniversalFrameworkLogger`  
- ✅ `src/universal_framework/utils/conversation_history_manager.py` - Uses `UniversalFrameworkLogger`

## Implementation Timeline

### Week 1: Configuration & Validation
- [ ] Create production configuration files
- [ ] Implement configuration validator
- [ ] Add configuration validation to startup
- [ ] Test configuration validation

### Week 1.5: CRITICAL - Observability Standardization
- [ ] **HIGH PRIORITY**: Convert legacy `logging.getLogger()` files (3 files)
  - [ ] `api/response_transformer.py`
  - [ ] `utils/state_access.py` 
  - [ ] `observability/otlp_router.py`
- [ ] **MEDIUM PRIORITY**: Convert `structlog.get_logger()` files (6 files)
  - [ ] `redis/session_storage.py`
  - [ ] `utils/session_logging.py`
  - [ ] `compliance/safe_mode.py`
  - [ ] `config/environment.py`
  - [ ] `config/toml_loader.py`
  - [ ] `llm/providers.py`
- [ ] **WORKFLOW FILES**: Consolidate multiple logging instances (4 files)
  - [ ] `api/routes/workflow.py` (17 instances)
  - [ ] `agents/intent_classifier.py` (9 instances)
  - [ ] `agents/strategy_generator.py` (2 instances)
  - [ ] `workflow/orchestrator.py` (mixed patterns)
- [ ] **VALIDATION**: Test all logging conversions
- [ ] **VERIFICATION**: Confirm enterprise features working (PII redaction, audit trails)

### Week 2: Error Recovery
- [ ] Implement production error recovery service
- [ ] Add circuit breaker patterns
- [ ] Integrate fallback mechanisms
- [ ] Test error recovery scenarios

### Week 3: Monitoring & Health Checks
- [ ] Implement production monitoring
- [ ] Add health check endpoints
- [ ] Integrate with existing monitoring
- [ ] Test monitoring integration

### Week 4: Production Testing
- [ ] End-to-end production testing
- [ ] Performance benchmarking
- [ ] Security validation
- [ ] Documentation updates

## Success Criteria

### Configuration Validation
- [ ] All production configurations validate successfully
- [ ] Redis connectivity verified
- [ ] LLM provider credentials validated
- [ ] Security policies enforced

### Observability Standardization ⭐ **CRITICAL**
- [ ] All 13 files converted to `UniversalFrameworkLogger` pattern
- [ ] Zero instances of `logging.getLogger()` remain in codebase
- [ ] Zero instances of direct `structlog.get_logger()` remain in non-enterprise components
- [ ] Enterprise features validated: PII redaction, audit trails, structured logging
- [ ] Workflow files consolidated to single logger instance per component
- [ ] Performance impact validated (<5ms overhead per log operation)
- [ ] Production 500 errors eliminated through consistent error handling

### Error Recovery
- [ ] Circuit breakers activate on failures
- [ ] Graceful fallback to simulation agents
- [ ] Comprehensive error reporting
- [ ] Recovery metrics tracked

### Monitoring
- [ ] Health check endpoints responding
- [ ] Metrics collection active
- [ ] Error rate monitoring functional
- [ ] Performance degradation alerts

## Risk Mitigation

### Observability Migration Risks ⚠️ **NEW**
1. **Production Disruption**: Implement changes during maintenance windows
2. **Performance Impact**: Validate <5ms logging overhead before deployment
3. **Feature Regression**: Ensure all existing logging functionality preserved
4. **Integration Failures**: Test enterprise features (PII redaction, audit trails) thoroughly
5. **Rollback Strategy**: Keep backup of original files with logging patterns

### Rollback Plan
1. **Configuration Issues**: Use environment variable overrides
2. **Error Recovery Issues**: Disable circuit breakers via feature flags  
3. **Monitoring Issues**: Disable metrics collection via configuration
4. **Observability Issues**: Revert to original logging patterns using backup files

### Testing Strategy
- Unit tests for all new components
- Integration tests with real Redis and LLM providers
- Load testing for production scenarios
- Security testing for compliance validation