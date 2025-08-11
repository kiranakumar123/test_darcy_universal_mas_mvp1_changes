"""Redis Contract Exceptions and Sanitization Utilities.

This module centralizes all Redis error classes and helper functions. It
implements password and connection-string sanitization to prevent
credentials from leaking into logs or error messages.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

__all__ = [
    "RedisError",
    "RedisContractError",
    "RedisValidationError",
    "RedisKeyError",
    "RedisVersionError",
    "RedisConnectionError",
    "RedisTimeoutError",
    "RedisAuthError",
    "RedisCapacityError",
    "RedisSerializationError",
    "RedisOperationError",
    "sanitize_redis_url",
    "sanitize_error_message",
]


class RedisError(Exception):
    """Base exception for all Redis-related errors."""

    def __init__(self, message: str, connection_info: str | None = None):
        # Sanitize the message to prevent credential leakage
        sanitized_message = sanitize_error_message(message, connection_info)
        super().__init__(sanitized_message)
        self.original_message = message
        self.connection_info = connection_info


class RedisContractError(RedisError):
    """Base exception for Redis contract violations."""


class RedisValidationError(RedisContractError):
    """Exception for schema validation failures."""


class RedisKeyError(RedisContractError):
    """Exception for key naming or format violations."""


class RedisVersionError(RedisContractError):
    """Exception for schema version incompatibilities."""


class RedisConnectionError(RedisError):
    """Exception for Redis connection issues."""


class RedisTimeoutError(RedisError):
    """Exception for Redis operation timeouts."""


class RedisAuthError(RedisError):
    """Exception for Redis authentication failures."""


class RedisCapacityError(RedisError):
    """Exception for Redis capacity or memory issues."""


class RedisSerializationError(RedisError):
    """Exception for serialization or deserialization failures."""


class RedisOperationError(RedisError):
    """General Redis operation failure."""


# ---------------------------------------------------------------------------
# Sanitization utilities
# ---------------------------------------------------------------------------


def sanitize_redis_url(url: str) -> str:
    """Sanitize Redis URL by masking password with *** for safe logging.

    Args:
        url: Redis connection URL (e.g., "redis://:password@host:6379/0")

    Returns:
        Sanitized URL with password masked (e.g., "redis://:***@host:6379/0")

    Examples:
        >>> sanitize_redis_url("redis://:secret@localhost:6379/0")
        "redis://:***@localhost:6379/0"
        >>> sanitize_redis_url("redis://user:pass@host:6379/0")
        "redis://user:***@host:6379/0"
        >>> sanitize_redis_url("redis://localhost:6379/0")
        "redis://localhost:6379/0"
    """
    if not url or not isinstance(url, str):
        return ""

    try:
        # Parse URL using urllib for robust handling
        parsed = urlparse(url)

        # If no password, return original URL
        if not parsed.password:
            return url

        # Build new netloc with masked password
        if parsed.username:
            netloc = f"{parsed.username}:***@{parsed.hostname}"
        else:
            netloc = f":***@{parsed.hostname}"

        # Add port if present
        if parsed.port:
            netloc += f":{parsed.port}"

        # Reconstruct URL with masked password
        sanitized = urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

        return sanitized

    except Exception:
        # Fallback to regex-based sanitization for malformed URLs
        return re.sub(r"(:\/\/)([^:@]*:)?[^@]*@", r"\1\2***@", url)


def sanitize_error_message(message: str, connection_info: str | None = None) -> str:
    """Sanitize error messages by removing or masking Redis credentials.

    Args:
        message: Original error message that may contain sensitive data
        connection_info: Optional connection string to specifically redact

    Returns:
        Sanitized error message safe for logging

    Examples:
        >>> sanitize_error_message("Failed to connect to redis://:secret@host:6379")
        "Failed to connect to redis://:***@host:6379"
        >>> sanitize_error_message("Auth failed", "redis://:pass@host:6379")
        "Auth failed"
    """
    if not message or not isinstance(message, str):
        return ""

    sanitized = message

    # If specific connection info provided, sanitize it first
    if connection_info:
        sanitized_conn = sanitize_redis_url(connection_info)
        sanitized = sanitized.replace(connection_info, sanitized_conn)

    # Find and sanitize any Redis URLs in the message
    redis_url_pattern = re.compile(r"redis[s]?://[^\s]+")

    def mask_url(match: re.Match[str]) -> str:
        return sanitize_redis_url(match.group(0))

    sanitized = redis_url_pattern.sub(mask_url, sanitized)

    # Additional patterns to catch other credential formats
    credential_patterns = [
        (r'password["\s]*[:=]["\s]*[^"\s]+', r'password="***"'),
        (r'pass["\s]*[:=]["\s]*[^"\s]+', r'pass="***"'),
        (r'auth["\s]*[:=]["\s]*[^"\s]+', r'auth="***"'),
    ]

    for pattern, replacement in credential_patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized
