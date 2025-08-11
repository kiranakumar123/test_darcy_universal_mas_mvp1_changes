"""GDPR-compliant PII detection and redaction engine."""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from re import Pattern
from typing import Any


@dataclass
class RedactionConfig:
    """Configuration for PII detection and redaction patterns."""

    email_pattern: str = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    phone_pattern: str = (
        r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"
    )
    ssn_pattern: str = r"\b\d{3}-\d{2}-\d{4}\b"
    credit_card_pattern: str = r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"

    hash_salt_rotation_hours: int = 24
    hash_algorithm: str = "sha256"

    email_replacement: str = "[EMAIL_REDACTED]"
    phone_replacement: str = "[PHONE_REDACTED]"
    ssn_replacement: str = "[SSN_REDACTED]"
    credit_card_replacement: str = "[CC_REDACTED]"
    session_replacement: str = "session_hash_{hash}"


class PIIDetector:
    """GDPR-compliant PII detection and redaction engine."""

    def __init__(self, config: RedactionConfig) -> None:
        self.config = config
        self.compiled_patterns = self._compile_patterns()
        self.hash_salt = self._generate_salt()
        self.salt_rotation_time = datetime.now()

    def _compile_patterns(self) -> dict[str, Pattern[str]]:
        """Compile regex patterns for efficient PII detection."""
        return {
            "email": re.compile(self.config.email_pattern, re.IGNORECASE),
            "phone": re.compile(self.config.phone_pattern),
            "ssn": re.compile(self.config.ssn_pattern),
            "credit_card": re.compile(self.config.credit_card_pattern),
        }

    def _generate_salt(self) -> str:
        """Generate cryptographically secure salt for hashing."""
        return secrets.token_hex(32)

    def _rotate_salt_if_needed(self) -> None:
        """Rotate hash salt based on configuration interval."""
        hours_elapsed = (
            datetime.now() - self.salt_rotation_time
        ).total_seconds() / 3600
        if hours_elapsed >= self.config.hash_salt_rotation_hours:
            self.hash_salt = self._generate_salt()
            self.salt_rotation_time = datetime.now()

    def redact_pii(self, text: str | None) -> str | None:
        """Redact PII from text using GDPR-compliant patterns."""
        if text is None or not isinstance(text, str):
            return text

        redacted = text
        redacted = self.compiled_patterns["email"].sub(
            self.config.email_replacement, redacted
        )
        redacted = self.compiled_patterns["phone"].sub(
            self.config.phone_replacement, redacted
        )
        redacted = self.compiled_patterns["ssn"].sub(
            self.config.ssn_replacement, redacted
        )
        redacted = self.compiled_patterns["credit_card"].sub(
            self.config.credit_card_replacement, redacted
        )
        return redacted

    def hash_session_id(self, session_id: str) -> str:
        """Create privacy-safe hash of session ID for audit tracking."""
        self._rotate_salt_if_needed()
        hash_input = f"{session_id}{self.hash_salt}".encode()
        hash_value = hashlib.sha256(hash_input).hexdigest()[:16]
        return f"session_hash_{hash_value}"

    def redact_metadata(
        self, metadata: dict[str, Any] | list[Any] | Any
    ) -> dict[str, Any] | list[Any] | Any:
        """Recursively redact PII from nested metadata structures."""
        if isinstance(metadata, dict):
            redacted: dict[str, Any] = {}
            for key, value in metadata.items():
                if isinstance(value, str):
                    redacted[key] = self.redact_pii(value)
                else:
                    redacted[key] = self.redact_metadata(value)
            return redacted
        if isinstance(metadata, list):
            return [self.redact_metadata(item) for item in metadata]
        return metadata
