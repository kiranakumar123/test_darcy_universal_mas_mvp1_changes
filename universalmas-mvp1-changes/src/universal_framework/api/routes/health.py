"""
Health and monitoring endpoints for the Universal Framework API.
"""

import sys
from datetime import datetime
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def detailed_health() -> dict[str, Any]:
    """Detailed health check with component status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system": {"python_version": sys.version, "platform": sys.platform},
        "framework": {"api_version": "0.1.0", "endpoints_active": True},
    }


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Kubernetes readiness probe endpoint."""
    return {"status": "ready", "timestamp": datetime.now().isoformat()}
