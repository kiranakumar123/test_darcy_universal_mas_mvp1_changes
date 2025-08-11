"""
Middleware configuration for the Universal Framework API.
"""

import os
import time
from collections.abc import Awaitable, Callable
from typing import Any

import jwt
from fastapi import HTTPException, Request, Response
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware

# Privacy logging now handled via dependency injection
from universal_framework.config.feature_flags import feature_flags


class SafeModeLogger:
    """Simple logger for safe mode without PII redaction."""

    def __init__(self) -> None:
        from universal_framework.core.logging_foundation import get_safe_logger

        self.logger = get_safe_logger("universal_framework.safe_mode")

    def log_session_event(
        self, session_id: str, event: str, metadata: dict[str, Any]
    ) -> None:
        """Log session event without PII redaction."""
        self.logger.info(event, session_id=session_id[:8], **metadata)


class EnhancedLoggingMiddleware(BaseHTTPMiddleware):
    """GDPR-compliant logging using PrivacySafeLogger."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        # Only enable PII-aware logging if feature is enabled
        if feature_flags.is_enabled("PII_REDACTION"):
            # Privacy logging now handled by UniversalFrameworkLogger
            self.privacy_logger = None  # Modern logger handles privacy
        else:
            # Safe mode - simple logging without PII redaction
            self.privacy_logger = SafeModeLogger()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.time()
        session_id = request.headers.get("X-Session-ID", "unknown")
        self.privacy_logger.log_session_event(
            session_id=session_id,
            event="api_request_start",
            metadata={"method": request.method, "path": request.url.path},
        )
        try:
            response = await call_next(request)
            exec_time = time.time() - start_time
            self.privacy_logger.log_session_event(
                session_id=session_id,
                event="api_request_complete",
                metadata={
                    "status_code": response.status_code,
                    "execution_time": exec_time,
                    "success": True,
                },
            )
            return response
        except Exception as exc:  # noqa: BLE001
            self.privacy_logger.log_session_event(
                session_id=session_id,
                event="api_request_error",
                metadata={"error": str(exc), "success": False},
            )
            raise


class SecurityMiddleware(BaseHTTPMiddleware):
    """Basic security headers middleware."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response


class EnterpriseAuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication via JWKS with configurable bypass."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        jwks_url = os.environ.get("JWT_JWKS_URL")
        self.jwks_client = PyJWKClient(jwks_url) if jwks_url else None

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Authenticate requests using JWT tokens and continue the chain."""

        public_paths = [
            "/",
            "/health",
            "/status",
            "/docs",
            "/redoc",
            "/metrics",
            "/openapi.json",
            "/favicon.ico",
        ]

        if (
            request.url.path.startswith("/api/v1/health")
            or request.url.path in public_paths
        ):
            return await call_next(request)

        if not self.jwks_client and os.environ.get("ENVIRONMENT") == "development":
            request.state.user = {"user_id": "dev_user"}
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthorized",
                    "message": "Missing authorization header",
                    "hint": "Include 'Authorization: Bearer <token>' header for protected endpoints",
                },
            )

        token = auth_header[7:]

        try:
            if self.jwks_client:
                signing_key = self.jwks_client.get_signing_key_from_jwt(token)
                decoded = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    issuer=os.environ.get("JWT_ISSUER"),
                    audience=os.environ.get("JWT_AUDIENCE"),
                )
            else:
                decoded = jwt.decode(token, options={"verify_signature": False})

            request.state.user_id = decoded.get("sub")
            request.state.user_roles = decoded.get("roles", [])
            request.state.user_permissions = decoded.get("permissions", [])
            request.state.auth_token = token

        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "token_expired",
                    "message": "JWT token has expired",
                    "hint": "Obtain a new token from your authentication provider",
                },
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_token",
                    "message": f"Invalid JWT token: {str(exc)}",
                    "hint": "Ensure token is properly formatted and not corrupted",
                },
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "authentication_failed",
                    "message": f"Token validation failed: {str(exc)}",
                    "hint": "Contact system administrator if problem persists",
                },
            ) from exc

        return await call_next(request)
