from datetime import datetime

import pytest

from universal_framework.contracts.state import EmailStrategy
from universal_framework.contracts.templates import StoredTemplate
from universal_framework.templates import TemplateStore
from universal_framework.utils.template_selector import (
    EmailTemplateSelector,
    EmailTemplateType,
)


class TestEmailTemplateSelector:
    def setup_method(self):
        self.selector = EmailTemplateSelector()

    @pytest.mark.parametrize(
        "content,expected",
        [
            ("New company policy regarding remote work", "policy_communication"),
            ("Training workshop on new procedures", "educational_content"),
            (
                "Important announcement about organizational changes",
                "executive_announcement",
            ),
            ("Team meeting scheduled for next week", "team_notification"),
            ("New product launch campaign", "marketing_promotion"),
            ("General business communication", "professional_standard"),
            ("", "professional_standard"),
        ],
    )
    def test_template_selection_logic(self, content: str, expected: str):
        strategy = EmailStrategy(
            overall_approach="",
            tone_strategy="",
            structure_strategy=[],
            messaging_strategy={},
            personalization_strategy={},
            estimated_impact="",
            confidence_score=1.0,
            content=content,
        )
        assert self.selector.select_template(strategy) == expected

    def test_template_selection_with_none_strategy(self):
        assert self.selector.select_template(None) == "professional_standard"

    def test_all_keywords_coverage(self):
        cases = [
            ("policy compliance regulation procedure", "policy_communication"),
            ("training workshop learning education", "educational_content"),
            ("announcement change important update", "executive_announcement"),
            ("team group department staff", "team_notification"),
            ("promotion launch campaign offer", "marketing_promotion"),
        ]
        for content, expected in cases:
            strategy = EmailStrategy(
                overall_approach="",
                tone_strategy="",
                structure_strategy=[],
                messaging_strategy={},
                personalization_strategy={},
                estimated_impact="",
                confidence_score=1.0,
                content=content,
            )
            assert self.selector.select_template(strategy) == expected

    def test_get_available_templates(self):
        templates = self.selector.get_available_templates()
        expected = [t.value for t in EmailTemplateType]
        assert set(templates) == set(expected)

    def test_validate_template(self):
        assert self.selector.validate_template("policy_communication") is True
        assert self.selector.validate_template("invalid") is False

    @pytest.mark.asyncio
    async def test_find_stored_template_integration(self):
        class FakeRedis:
            def __init__(self) -> None:
                self.store = {}

            async def execute_command(self, command: str, *args, **kwargs):
                if command == "KEYS":
                    return list(self.store)
                if command == "GET":
                    return self.store.get(args[0])
                if command == "SET":
                    self.store[args[0]] = args[1]
                    return True
                raise NotImplementedError(command)

        adapter = FakeRedis()
        store = TemplateStore(adapter)
        selector = EmailTemplateSelector(store)
        template = StoredTemplate(
            template_id="tmp10",
            template_type="policy_communication",
            subject_template="Sub",
            body_template="Body",
            variables=[],
            metadata={},
            created_date=datetime.now(),
            last_used=datetime.now(),
            usage_count=0,
        )
        await store.store_template(template)
        strategy = EmailStrategy(
            overall_approach="",
            tone_strategy="",
            structure_strategy=[],
            messaging_strategy={},
            personalization_strategy={},
            estimated_impact="",
            confidence_score=1.0,
            content="New policy announcement",
        )
        found = await selector.find_stored_template(strategy)
        assert found is not None
        assert found.template_id == "tmp10"
