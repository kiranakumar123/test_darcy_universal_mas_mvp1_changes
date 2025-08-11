from __future__ import annotations

import re
from enum import Enum

from universal_framework.contracts.state import EmailStrategy
from universal_framework.contracts.templates import StoredTemplate
from universal_framework.templates import TemplateStore


class EmailTemplateType(Enum):
    """Email template types for consistent selection."""

    POLICY_COMMUNICATION = "policy_communication"
    EDUCATIONAL_CONTENT = "educational_content"
    EXECUTIVE_ANNOUNCEMENT = "executive_announcement"
    TEAM_NOTIFICATION = "team_notification"
    MARKETING_PROMOTION = "marketing_promotion"
    PROFESSIONAL_STANDARD = "professional_standard"


class EmailTemplateSelector:
    """Centralized email template selection logic for Universal Framework."""

    def __init__(self, template_store: TemplateStore | None = None) -> None:
        self._template_keywords = {
            EmailTemplateType.POLICY_COMMUNICATION: {
                "policy",
                "procedure",
                "compliance",
                "regulation",
            },
            EmailTemplateType.EDUCATIONAL_CONTENT: {
                "training",
                "workshop",
                "learning",
                "education",
            },
            EmailTemplateType.EXECUTIVE_ANNOUNCEMENT: {
                "announcement",
                "change",
                "important",
                "update",
            },
            EmailTemplateType.TEAM_NOTIFICATION: {
                "team",
                "group",
                "department",
                "staff",
            },
            EmailTemplateType.MARKETING_PROMOTION: {
                "promotion",
                "launch",
                "campaign",
                "offer",
            },
        }
        self.template_store = template_store

    def select_template(self, strategy: EmailStrategy | None) -> str:
        """Select appropriate template based on strategy content."""
        if not strategy or not strategy.content:
            return EmailTemplateType.PROFESSIONAL_STANDARD.value

        content_keywords = set(re.findall(r"\b\w+\b", strategy.content.lower()))
        selected_template = EmailTemplateType.PROFESSIONAL_STANDARD

        for template_type, keywords in self._template_keywords.items():
            if any(keyword in content_keywords for keyword in keywords):
                selected_template = template_type
                break

        return selected_template.value

    def get_available_templates(self) -> list[str]:
        """Return list of all available template types."""
        return [template.value for template in EmailTemplateType]

    def validate_template(self, template_name: str) -> bool:
        """Validate if template name is supported."""
        return template_name in [template.value for template in EmailTemplateType]

    async def find_stored_template(
        self, strategy: EmailStrategy
    ) -> StoredTemplate | None:
        """Find stored template using optional TemplateStore."""
        if self.template_store is None:
            return None
        template_type = self.select_template(strategy)
        return await self.template_store.find_template_by_type(template_type)
