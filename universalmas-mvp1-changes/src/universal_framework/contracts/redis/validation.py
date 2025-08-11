"""
Centralized Validation Library
=============================

Enterprise-grade validation for all Redis operations.
Enforces schema compliance and data integrity.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .exceptions import RedisValidationError, RedisVersionError

# Load JSON schemas
SCHEMA_DIR = Path(__file__).parent
try:
    with open(SCHEMA_DIR / "schemas.json", encoding="utf-8") as f:
        SCHEMAS = json.load(f)
except json.JSONDecodeError as e:
    raise ValueError(
        f"Invalid JSON in Redis schemas file {SCHEMA_DIR / 'schemas.json'}: {e}. "
        f"Please check the file for syntax errors, especially property names "
        f"that should be enclosed in double quotes."
    ) from e
except FileNotFoundError:
    raise FileNotFoundError(
        f"Redis schemas file not found: {SCHEMA_DIR / 'schemas.json'}. "
        f"Please ensure the file exists and is properly deployed."
    )


class SchemaValidator:
    """JSON Schema validator for Redis data."""

    def __init__(self) -> None:
        self.schemas = SCHEMAS["definitions"]
        self.current_version = 1

    def validate_session_message(self, data: dict[str, Any]) -> list[str]:
        """Validate session message against schema."""
        try:
            jsonschema.validate(data, self.schemas["SessionMessage"])
            return []
        except jsonschema.ValidationError as e:
            return [f"SessionMessage validation error: {e.message}"]
        except Exception as e:
            return [f"SessionMessage validation failed: {str(e)}"]

    def validate_session_data(self, data: dict[str, Any]) -> list[str]:
        """Validate session data against schema."""
        try:
            jsonschema.validate(data, self.schemas["SessionData"])
            return []
        except jsonschema.ValidationError as e:
            return [f"SessionData validation error: {e.message}"]
        except Exception as e:
            return [f"SessionData validation failed: {str(e)}"]

    def validate_session_metadata(self, data: dict[str, Any]) -> list[str]:
        """Validate session metadata against schema."""
        try:
            jsonschema.validate(data, self.schemas["SessionMetadata"])
            return []
        except jsonschema.ValidationError as e:
            return [f"SessionMetadata validation error: {e.message}"]
        except Exception as e:
            return [f"SessionMetadata validation failed: {str(e)}"]


class SessionValidator:
    """Business logic validator for session operations."""

    def __init__(self) -> None:
        self.schema_validator = SchemaValidator()

    def validate_session_id(self, session_id: str) -> list[str]:
        """Validate session ID format (UUID4)."""
        errors = []
        if not session_id:
            errors.append("Session ID cannot be empty")
            return errors

        # Check UUID4 format
        import re

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        if not re.match(uuid_pattern, session_id.lower()):
            errors.append("Session ID must be valid UUID4 format")

        return errors

    def validate_user_id(self, user_id: str) -> list[str]:
        """Validate user ID format."""
        errors = []
        if not user_id or not user_id.strip():
            errors.append("User ID cannot be empty")
        if len(user_id) > 255:
            errors.append("User ID cannot exceed 255 characters")
        return errors

    def validate_ttl(self, ttl_hours: int) -> list[str]:
        """Validate TTL value."""
        errors = []
        if ttl_hours <= 0:
            errors.append("TTL must be positive")
        if ttl_hours > 8760:  # 1 year
            errors.append("TTL cannot exceed 1 year (8760 hours)")
        return errors

    def validate_message_content_size(self, content: str) -> list[str]:
        """Validate message content size limits."""
        errors = []
        if len(content.encode("utf-8")) > 1024 * 1024:  # 1MB limit
            errors.append("Message content cannot exceed 1MB")
        return errors

    def validate_phase_completion(self, completion: dict[str, float]) -> list[str]:
        """Validate phase completion percentages."""
        errors = []
        valid_phases = {
            "initialization",
            "discovery",
            "analysis",
            "generation",
            "review",
            "delivery",
            "completion",
        }

        for phase, value in completion.items():
            if phase not in valid_phases:
                errors.append(f"Invalid workflow phase: {phase}")
            if not isinstance(value, int | float) or value < 0.0 or value > 1.0:
                errors.append(
                    f"Phase completion must be 0.0-1.0, got {value} for {phase}"
                )

        return errors


def serialize_message(message: BaseMessage) -> dict[str, Any]:
    """Serialize LangChain message for Redis storage."""
    message_data = {
        "id": getattr(message, "id", None)
        or f"{type(message).__name__}_{datetime.now().timestamp()}",
        "type": type(message).__name__,
        "content": message.content,
        "additional_kwargs": getattr(message, "additional_kwargs", {}),
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            **getattr(message, "metadata", {}),
        },
        "schema_version": 1,
    }

    # Validate before returning
    validator = SchemaValidator()
    errors = validator.validate_session_message(message_data)
    if errors:
        raise RedisValidationError(f"Message serialization failed: {errors}")

    return message_data


def deserialize_message(data: dict[str, Any]) -> BaseMessage:
    """Deserialize message from Redis storage."""
    # Validate schema first
    validator = SchemaValidator()
    errors = validator.validate_session_message(data)
    if errors:
        raise RedisValidationError(f"Message deserialization failed: {errors}")

    # Check version compatibility
    schema_version = data.get("schema_version", 1)
    if schema_version > 1:
        raise RedisVersionError(f"Unsupported schema version: {schema_version}")

    # Create appropriate message type
    msg_type = data["type"]
    content = data["content"]
    additional_kwargs = data.get("additional_kwargs", {})

    if msg_type == "HumanMessage":
        return HumanMessage(content=content, additional_kwargs=additional_kwargs)
    elif msg_type == "AIMessage":
        return AIMessage(content=content, additional_kwargs=additional_kwargs)
    elif msg_type == "SystemMessage":
        return SystemMessage(content=content, additional_kwargs=additional_kwargs)
    else:
        return HumanMessage(content=content, additional_kwargs=additional_kwargs)


def validate_session_data(data: dict[str, Any]) -> list[str]:
    """Validate complete session data."""
    validator = SessionValidator()
    all_errors = []

    # Schema validation
    all_errors.extend(validator.schema_validator.validate_session_data(data))

    # Business logic validation
    if "session_id" in data:
        all_errors.extend(validator.validate_session_id(data["session_id"]))

    if "user_id" in data:
        all_errors.extend(validator.validate_user_id(data["user_id"]))

    if "phase_completion" in data:
        all_errors.extend(validator.validate_phase_completion(data["phase_completion"]))

    return all_errors


def validate_message_data(data: dict[str, Any]) -> list[str]:
    """Validate message data."""
    validator = SessionValidator()
    all_errors = []

    # Schema validation
    all_errors.extend(validator.schema_validator.validate_session_message(data))

    # Content size validation
    if "content" in data:
        all_errors.extend(validator.validate_message_content_size(data["content"]))

    return all_errors


def sanitize_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize data for safe logging (remove sensitive information)."""
    sanitized = data.copy()

    # Remove sensitive fields
    sensitive_fields = ["auth_token", "password", "api_key"]
    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = "***"

    # Truncate long content
    if "content" in sanitized and len(str(sanitized["content"])) > 100:
        sanitized["content"] = str(sanitized["content"])[:100] + "..."

    return sanitized
