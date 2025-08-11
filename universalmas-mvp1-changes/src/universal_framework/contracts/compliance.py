"""Enterprise compliance contracts and data structures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ComplianceConfig:
    """Enterprise compliance configuration."""

    privacy_logging_enabled: bool = True
    pii_redaction_enabled: bool = True
    hash_session_ids: bool = True
    gdpr_compliance_required: bool = True
    audit_trail_required: bool = True
    soc2_compliance: bool = True
    iso_27001_compliance: bool = True
    gdpr_article_25: bool = True
    gdpr_article_32: bool = True


@dataclass
class PrivacyLogEntry:
    """GDPR-compliant log entry structure."""

    session_hash: str
    event: str
    timestamp: str
    metadata: dict[str, Any]
    compliance_metadata: dict[str, bool]
    pii_redacted: bool = True
    gdpr_compliant: bool = True
