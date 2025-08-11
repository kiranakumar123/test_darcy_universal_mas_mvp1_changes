"""Workflow configuration for the Universal Framework.

Provides a centralized source of truth for all environment-driven settings.
Fields are loaded from environment variables as strings and validated at runtime.
Includes Redis, security, performance, logging, and session management options.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from universal_framework.contracts.redis.exceptions import sanitize_redis_url


@dataclass
class WorkflowConfig:
    """Complete configuration for Universal Framework components.

    All settings are sourced from environment variables. Numeric values and
    complex validation rules are checked in :meth:`validate`. This design keeps
    instantiation safe and prevents early crashes from malformed variables. The
    configuration covers Redis connectivity, security controls, performance
    tuning, logging, and operational parameters required for running the
    Universal Framework in different environments.
    """

    # Redis
    enable_redis_optimization: bool = field(
        default_factory=lambda: os.getenv("ENABLE_REDIS_OPTIMIZATION", "false").lower()
        == "true"
    )
    redis_url: str | None = field(default_factory=lambda: os.getenv("REDIS_URL"))
    redis_host: str = field(
        default_factory=lambda: os.getenv("REDIS_HOST", "localhost")
    )
    redis_port: str = field(default_factory=lambda: os.getenv("REDIS_PORT", "6379"))
    redis_db: str = field(default_factory=lambda: os.getenv("REDIS_DB", "0"))
    redis_password: str | None = field(
        default_factory=lambda: os.getenv("REDIS_PASSWORD")
    )
    redis_ttl_hours: str = field(
        default_factory=lambda: os.getenv("REDIS_TTL_HOURS", "24")
    )

    # Core Framework
    enable_debug: bool = field(
        default_factory=lambda: os.getenv("ENABLE_DEBUG", "false").lower() == "true"
    )
    enable_parallel_processing: bool = field(
        default_factory=lambda: os.getenv("ENABLE_PARALLEL_PROCESSING", "false").lower()
        == "true"
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    enable_metrics: bool = field(
        default_factory=lambda: os.getenv("ENABLE_METRICS", "true").lower() == "true"
    )

    # Security
    jwt_secret_key: str | None = field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY")
    )
    session_timeout_hours: str = field(
        default_factory=lambda: os.getenv("SESSION_TIMEOUT_HOURS", "8")
    )
    enable_auth_validation: bool = field(
        default_factory=lambda: os.getenv("ENABLE_AUTH_VALIDATION", "true").lower()
        == "true"
    )

    # Performance
    max_execution_time_seconds: str = field(
        default_factory=lambda: os.getenv("MAX_EXECUTION_TIME_SECONDS", "30")
    )
    agent_timeout_seconds: str = field(
        default_factory=lambda: os.getenv("AGENT_TIMEOUT_SECONDS", "5")
    )
    max_concurrent_sessions: str = field(
        default_factory=lambda: os.getenv("MAX_CONCURRENT_SESSIONS", "1000")
    )
    session_cache_size: str = field(
        default_factory=lambda: os.getenv("SESSION_CACHE_SIZE", "100")
    )

    # Session Management
    session_cleanup_interval: str = field(
        default_factory=lambda: os.getenv("SESSION_CLEANUP_INTERVAL", "3600")
    )
    max_session_age_hours: str = field(
        default_factory=lambda: os.getenv("MAX_SESSION_AGE_HOURS", "24")
    )

    def validate(self) -> list[str]:
        """Validate configuration values and return a list of issues."""

        errors: list[str] = []

        if self.enable_redis_optimization:
            if self.redis_url:
                if not self.redis_url.startswith(("redis://", "rediss://")):
                    errors.append("redis_url must start with redis:// or rediss://")
            else:
                if not self.redis_host.strip():
                    errors.append("redis_host required when Redis enabled")
                try:
                    port = int(self.redis_port)
                    if not (1 <= port <= 65535):
                        errors.append("redis_port must be 1-65535")
                except ValueError:
                    errors.append("redis_port must be a valid integer")
                try:
                    db = int(self.redis_db)
                    if db < 0:
                        errors.append("redis_db must be non-negative")
                except ValueError:
                    errors.append("redis_db must be a valid integer")

        numeric_validations = {
            "redis_ttl_hours": (1, 8760),
            "session_timeout_hours": (1, 72),
            "max_execution_time_seconds": (1, 300),
            "agent_timeout_seconds": (1, 30),
            "session_cleanup_interval": (60, 86400),
            "max_session_age_hours": (1, 8760),
            "max_concurrent_sessions": (1, 100000),
            "session_cache_size": (0, 10000),
        }
        for field_name, (min_val, max_val) in numeric_validations.items():
            try:
                value = int(getattr(self, field_name))
                if not (min_val <= value <= max_val):
                    errors.append(
                        f"{field_name} must be between {min_val} and {max_val}"
                    )
            except ValueError:
                errors.append(f"{field_name} must be a valid integer")

        if not self.jwt_secret_key and not self.enable_debug:
            errors.append("jwt_secret_key required in non-debug mode")

        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"log_level must be one of: {', '.join(valid_log_levels)}")

        return errors

    def get_sanitized_redis_url(self) -> str:
        """Return Redis URL with password masked for safe logging."""
        connection = self.redis_url
        if connection is None:
            auth = f":{self.redis_password}@" if self.redis_password else ""
            connection = (
                f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
            )
        return sanitize_redis_url(connection)

    @property
    def redis_connection_url(self) -> str:
        """Connection string for Redis including password when provided."""
        if self.redis_url:
            return self.redis_url
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
