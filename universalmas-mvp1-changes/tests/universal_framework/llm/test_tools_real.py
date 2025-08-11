import pytest

from universal_framework.llm.tools import (
    EmailValidationTool,
    RequirementsExtractionTool,
)


class TestLLMToolsReal:
    """Validate LLM tools with real execution."""

    @pytest.mark.asyncio
    async def test_requirement_extraction_tool_real(self):
        tool = RequirementsExtractionTool()
        user_message = (
            "Please send an email to john@example.com about quarterly results."
        )
        result = await tool._arun(user_message)
        assert "audience" in result
        assert "purpose" in result

    @pytest.mark.asyncio
    async def test_email_validation_tool_real(self):
        tool = EmailValidationTool()
        valid_email = "Subject: Update\nHello team,\nBest regards"
        result = await tool._arun(valid_email)
        assert "validation" in result.lower() or "passed" in result.lower()
