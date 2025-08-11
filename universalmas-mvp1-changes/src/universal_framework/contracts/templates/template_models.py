from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class StoredTemplate:
    """Lightweight stored template for enterprise pre-approval."""

    template_id: str
    template_type: str
    subject_template: str
    body_template: str
    variables: list[str]
    metadata: dict[str, Any]
    created_date: datetime
    last_used: datetime
    usage_count: int

    def copy_with_usage_update(self) -> StoredTemplate:
        """Return a copy with usage stats updated."""
        return self.__class__(
            template_id=self.template_id,
            template_type=self.template_type,
            subject_template=self.subject_template,
            body_template=self.body_template,
            variables=self.variables,
            metadata=self.metadata,
            created_date=self.created_date,
            last_used=datetime.now(),
            usage_count=self.usage_count + 1,
        )
