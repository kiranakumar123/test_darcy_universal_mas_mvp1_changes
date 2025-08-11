from __future__ import annotations

from typing import Any

from ..contracts.session.interfaces import DataClassification


class DataClassificationManager:
    """Manage classification policies for session data."""

    TTL_CLASSIFICATIONS: dict[DataClassification, int] = {
        DataClassification.PUBLIC: 3600,
        DataClassification.CONFIDENTIAL: 14400,
        DataClassification.RESTRICTED: 1800,
        DataClassification.HIGHLY_SENSITIVE: 900,
    }

    def get_ttl_for_classification(self, classification: DataClassification) -> int:
        """Return TTL seconds based on classification."""
        return self.TTL_CLASSIFICATIONS.get(classification, 3600)

    def classify_session_data(self, data: dict[str, Any]) -> DataClassification:
        """Trivial classification using presence of PII markers."""
        if self._contains_pii(data):
            return DataClassification.HIGHLY_SENSITIVE
        return DataClassification.CONFIDENTIAL

    def _contains_pii(self, data: dict[str, Any]) -> bool:
        """Placeholder PII detection."""
        text = str(data)
        return any(term in text.lower() for term in {"ssn", "password", "secret"})
