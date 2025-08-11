"""Tools for LangChain agents following modern Python patterns."""

import json
from enum import Enum

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from universal_framework.contracts.state import UniversalWorkflowState

from ..core.logging_foundation import get_safe_logger

logger = get_safe_logger(__name__)


class QueryType(Enum):
    """Types of state queries."""

    REQUIREMENTS = "requirements"
    STRATEGY = "strategy"
    PHASE = "phase"
    CONTEXT = "context"
    UNKNOWN = "unknown"


class EmailValidationInput(BaseModel, frozen=True):
    """Input for email validation tool."""

    email_content: str = Field(description="Email content to validate")


class EmailValidationTool(BaseTool):
    """Tool to validate email format and content."""

    name: str = "email_validator"
    description: str = (
        "Validates email content for formatting, tone, and professionalism"
    )
    args_schema: type[BaseModel] = EmailValidationInput

    def _run(self, email_content: str) -> str:
        """Validate email content using modern patterns."""

        issues: list[str] = []

        # Use match/case for validation logic
        match len(email_content):
            case length if length < 10:
                issues.append("Email content too short")
            case length if length > 5000:
                issues.append("Email content too long")

        # Pattern matching for content validation
        has_greeting = any(
            word in email_content.lower()
            for word in ["subject:", "dear", "hello", "hi"]
        )

        has_closing = any(
            word in email_content.lower()
            for word in ["regards", "best", "thank", "sincerely"]
        )

        match (has_greeting, has_closing):
            case (False, _):
                issues.append("Missing greeting or subject")
            case (_, False):
                issues.append("Missing professional closing")
            case (True, True):
                logger.info(
                    "email_validation_passed", content_length=len(email_content)
                )

        match issues:
            case []:
                return "Email validation passed - content looks professional"
            case issue_list:
                logger.warning("email_validation_failed", issues=issue_list)
                return f"Email validation failed: {', '.join(issue_list)}"


class RequirementsExtractionInput(BaseModel, frozen=True):
    """Input for requirements extraction tool."""

    user_request: str = Field(description="User's email request to analyze")


class RequirementsExtractionTool(BaseTool):
    """Tool to extract structured requirements from user input."""

    name: str = "requirements_extractor"
    description: str = (
        "Extracts structured email requirements (audience, tone, purpose) from user input"
    )
    args_schema: type[BaseModel] = RequirementsExtractionInput

    def _run(self, user_request: str) -> str:
        """Extract requirements using modern pattern matching."""

        # Initialize with defaults
        requirements = {
            "audience": "professional",
            "tone": "professional",
            "purpose": "communication",
            "key_points": [],
        }

        request_lower = user_request.lower()

        # Audience detection with pattern matching
        audience_keywords = [
            (["team", "colleagues", "staff"], "internal_team"),
            (["client", "customer", "external"], "external_clients"),
            (["executive", "leadership", "management"], "executives"),
        ]

        for keywords, audience_type in audience_keywords:
            if any(word in request_lower for word in keywords):
                requirements["audience"] = audience_type
                break

        # Tone detection
        match request_lower:
            case text if any(
                word in text for word in ["casual", "friendly", "informal"]
            ):
                requirements["tone"] = "casual"
            case text if any(
                word in text for word in ["formal", "official", "corporate"]
            ):
                requirements["tone"] = "formal"
            case _:
                requirements["tone"] = "professional"  # default

        # Purpose detection
        match request_lower:
            case text if any(
                word in text for word in ["announce", "announcement", "inform"]
            ):
                requirements["purpose"] = "announcement"
            case text if any(word in text for word in ["update", "status", "progress"]):
                requirements["purpose"] = "update"
            case text if any(word in text for word in ["thank", "appreciation"]):
                requirements["purpose"] = "appreciation"
            case _:
                requirements["purpose"] = "communication"

        logger.info(
            "requirements_extracted",
            audience=requirements["audience"],
            tone=requirements["tone"],
            purpose=requirements["purpose"],
        )

        return json.dumps(requirements, indent=2)


class StateAccessInput(BaseModel, frozen=True):
    """Input for state access tool."""

    query: str = Field(description="What to retrieve from workflow state")


class StateAccessTool(BaseTool):
    """Tool to access current workflow state."""

    name: str = "state_accessor"
    description: str = (
        "Access current workflow state, context, and previous agent outputs"
    )
    args_schema: type[BaseModel] = StateAccessInput

    def __init__(self, state: UniversalWorkflowState):
        super().__init__()
        self.state = state

    def _run(self, query: str) -> str:
        """Access workflow state using pattern matching."""

        # Classify query type
        query_lower = query.lower()

        query_type = QueryType.UNKNOWN
        match query_lower:
            case q if "requirements" in q:
                query_type = QueryType.REQUIREMENTS
            case q if "strategy" in q:
                query_type = QueryType.STRATEGY
            case q if "phase" in q:
                query_type = QueryType.PHASE
            case q if "context" in q:
                query_type = QueryType.CONTEXT

        # Process query based on type
        match query_type:
            case QueryType.REQUIREMENTS:
                result = self.state.context_data.get("collected_requirements", {})
                logger.info("state_access_requirements", has_data=bool(result))
                return json.dumps(result, indent=2)

            case QueryType.STRATEGY:
                result = self.state.context_data.get("generated_strategy", {})
                logger.info("state_access_strategy", has_data=bool(result))
                return json.dumps(result, indent=2)

            case QueryType.PHASE:
                logger.info("state_access_phase", phase=self.state.workflow_phase.value)
                return f"Current phase: {self.state.workflow_phase.value}"

            case QueryType.CONTEXT:
                logger.info(
                    "state_access_context",
                    context_keys=list(self.state.context_data.keys()),
                )
                return json.dumps(self.state.context_data, indent=2)

            case QueryType.UNKNOWN | _:
                available_data = ["requirements", "strategy", "phase", "context"]
                logger.warning("state_access_unknown_query", query=query)
                return (
                    f"Available state data: {', '.join(available_data)}. "
                    f"Current phase: {self.state.workflow_phase.value}"
                )
