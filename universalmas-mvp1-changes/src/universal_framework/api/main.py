"""Universal Multi-Agent System Framework - FastAPI Application."""

from __future__ import annotations

# ruff: noqa: B008
import sys
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from universal_framework.api.dependencies import (
    get_redis_adapter,
    get_session_manager,
    get_session_storage,
    initialize_redis_connection,
)
from universal_framework.api.middleware import (
    EnhancedLoggingMiddleware,
    EnterpriseAuthMiddleware,
    SecurityMiddleware,
)
from universal_framework.api.models.responses import (
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowRequest,
)
from universal_framework.api.routes.health import router as health_router
from universal_framework.api.routes.langgraph_studio import router as studio_router
from universal_framework.api.routes.sessions import router as sessions_router
from universal_framework.api.routes.workflow import (
    execute_workflow_hybrid,
)
from universal_framework.api.routes.workflow import (
    router as workflow_router,
)
from universal_framework.config.feature_flags import feature_flags, is_safe_mode

# Make OpenTelemetry tracing optional
try:
    from universal_framework.api.tracing import setup_opentelemetry

    _opentelemetry_available = True
except ImportError:
    _opentelemetry_available = False

from universal_framework.redis.session_storage import SessionStorage
from universal_framework.session.session_manager import EnterpriseSessionManager

# Import framework components with graceful fallback
FRAMEWORK_AVAILABLE = True

# Initialize enterprise logging before application startup
try:
    from universal_framework.observability.logging_config import (
        initialize_enterprise_logging,
    )

    initialize_enterprise_logging()
except ImportError:
    # Fallback: basic logging if enterprise logging unavailable
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

# Initialize FastAPI application with proper JSON serialization
app = FastAPI(
    title="Universal Multi-Agent System Framework",
    description="Enterprise-grade multi-agent system with 33+ universal agents"
    + (" [SAFE MODE]" if is_safe_mode() else ""),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Setup observability
if _opentelemetry_available and feature_flags.is_enabled("LANGSMITH_TRACING"):
    setup_opentelemetry(app)

# Configure CORS for development (always enabled)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core middleware (always enabled)
app.add_middleware(EnhancedLoggingMiddleware)
app.add_middleware(SecurityMiddleware)

# Enterprise middleware (conditional based on feature flags)
if feature_flags.is_enabled("ENTERPRISE_AUTH_MIDDLEWARE"):
    try:
        app.add_middleware(EnterpriseAuthMiddleware)
    except Exception as e:
        print(f"Warning: Could not load EnterpriseAuthMiddleware: {e}")

if feature_flags.is_enabled("LANGSMITH_TRACING"):
    try:
        from universal_framework.compliance.pii_detector import (
            PIIDetector,
            RedactionConfig,
        )
        from universal_framework.observability.enterprise_langsmith import (
            LangSmithCircuitBreaker,
        )
        from universal_framework.observability.langsmith_middleware import (
            LangSmithAPITracingMiddleware,
        )

        app.add_middleware(
            LangSmithAPITracingMiddleware,
            pii_detector=PIIDetector(RedactionConfig()),
            circuit_breaker=LangSmithCircuitBreaker({}),
        )
    except Exception as e:
        print(f"Warning: Could not load LangSmith middleware: {e}")

app.include_router(health_router)
app.include_router(workflow_router)
app.include_router(sessions_router)
app.include_router(studio_router)  # LangGraph Studio endpoints


# Global exception handler (narrowed to avoid catching response serialization)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions gracefully, excluding response serialization issues."""

    # Don't intercept FastAPI's own serialization errors - let them be handled normally
    if isinstance(exc, TypeError | ValueError) and any(
        keyword in str(exc).lower()
        for keyword in ["json", "serialize", "encode", "pydantic"]
    ):
        # Re-raise to let FastAPI handle response serialization properly
        raise exc

    error_info = {
        "error": "Internal server error",
        "message": str(exc),
        "timestamp": datetime.now().isoformat(),
    }

    # Add safe mode information to errors for debugging
    if is_safe_mode():
        error_info["safe_mode"] = True
        error_info["note"] = "Running in safe mode - some enterprise features disabled"

    return JSONResponse(
        status_code=500,
        content=error_info,
    )


# Health check endpoint
@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint for container orchestration."""
    health_info = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "framework_available": FRAMEWORK_AVAILABLE,
        "python_version": sys.version,
        "components": {
            "workflow_builder": FRAMEWORK_AVAILABLE,
            "state_management": FRAMEWORK_AVAILABLE,
            "llm_config": FRAMEWORK_AVAILABLE,
        },
    }

    # Include safe mode information
    if is_safe_mode():
        from universal_framework.config.feature_flags import get_safe_mode_status

        health_info["safe_mode"] = get_safe_mode_status()

    return health_info


# Safe mode status endpoint
@app.get("/safe-mode-status")
async def safe_mode_status() -> dict[str, Any]:
    """Get current safe mode configuration and feature status."""
    from universal_framework.config.feature_flags import get_safe_mode_status

    return get_safe_mode_status()


# Status endpoint
@app.get("/status")
async def status_check() -> dict[str, Any]:
    """Detailed status information for monitoring."""
    status_info = {
        "framework": {
            "name": "Universal Multi-Agent System Framework",
            "version": "0.1.0",
            "available": FRAMEWORK_AVAILABLE,
            "safe_mode": is_safe_mode(),
        },
        "api": {
            "status": "running",
            "endpoints": ["/health", "/status", "/safe-mode-status", "/docs", "/redoc"],
            "timestamp": datetime.now().isoformat(),
        },
        "workflow": {
            "builder_available": FRAMEWORK_AVAILABLE,
            "phases": (
                [
                    "initialization",
                    "discovery",
                    "analysis",
                    "generation",
                    "review",
                    "delivery",
                    "completion",
                ]
                if FRAMEWORK_AVAILABLE
                else []
            ),
            "agent_count": "33+" if FRAMEWORK_AVAILABLE else "unknown",
        },
    }

    # Include feature flags status
    status_info["features"] = feature_flags.get_feature_status()

    return status_info


# Root endpoint
@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with basic information."""
    return {
        "message": "Universal Multi-Agent System Framework API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "status": "/status",
    }


@app.post("/workflow/execute")
async def execute_workflow(
    request: WorkflowRequest | WorkflowExecuteRequest,
    background_tasks: BackgroundTasks,
    session_manager: EnterpriseSessionManager = Depends(
        get_session_manager
    ),  # noqa: B008
    session_storage: SessionStorage = Depends(get_session_storage),
) -> WorkflowExecuteResponse:
    """Backward-compatible workflow execution endpoint."""
    if isinstance(request, WorkflowExecuteRequest):
        enhanced_request = request
    else:
        enhanced_request = WorkflowExecuteRequest(
            session_id=request.session_id or str(uuid4()),
            message=request.message,
            context=request.context,
            workflow_type="document_generation",
            target_deliverables=None,
        )
    return await execute_workflow_hybrid(
        enhanced_request, background_tasks, session_manager, session_storage
    )


# Startup event
@app.on_event("startup")
async def startup_event() -> None:
    """Initialize application on startup."""
    await initialize_redis_connection()


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up on application shutdown."""
    adapter = get_redis_adapter()
    if adapter:
        await adapter.disconnect()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
