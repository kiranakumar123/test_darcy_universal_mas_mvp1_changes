"""
API Response Transformer for Universal Framework.
Transforms internal agent responses to clean frontend API structure.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from universal_framework.observability import UniversalFrameworkLogger

logger = UniversalFrameworkLogger("response_transformer")


class APIResponseTransformer:
    """
    Transform internal agent responses to clean frontend API structure.

    Solves the core problem where frontend receives internal metadata
    instead of actual user-facing message content.

    Features JSON template-based responses for rich UX instead of generic
    completion_percentage responses.
    """

    _templates_cache: dict[str, dict[str, Any]] = {}
    _templates_loaded: bool = False

    @classmethod
    def load_templates(cls) -> None:
        """
        Load JSON templates from config/ux/ux_templates/ directory.

        Templates provide rich UX responses instead of generic completion messages.
        Templates are cached for performance and loaded on first use.
        """
        if cls._templates_loaded:
            return

        templates_dir = Path("config/ux/ux_templates")
        if not templates_dir.exists():
            logger.warning(f"Templates directory not found: {templates_dir}")
            cls._templates_loaded = True
            return

        template_files = templates_dir.glob("*.json")
        loaded_count = 0

        for template_file in template_files:
            try:
                with open(template_file, encoding="utf-8") as f:
                    template_data = json.load(f)
                    template_type = template_data.get("template_type")
                    if template_type:
                        cls._templates_cache[template_type] = template_data
                        loaded_count += 1
                        logger.info(
                            f"Loaded template: {template_type} from {template_file.name}"
                        )
                    else:
                        logger.warning(
                            f"Template missing 'template_type': {template_file.name}"
                        )
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load template {template_file}: {e}")

        cls._templates_loaded = True
        logger.info(f"Loaded {loaded_count} UX templates")

    @classmethod
    def get_template(cls, template_type: str) -> dict[str, Any] | None:
        """
        Get a specific template by type.

        Args:
            template_type: Type of template to retrieve

        Returns:
            Template data or None if not found
        """
        if not cls._templates_loaded:
            cls.load_templates()

        return cls._templates_cache.get(template_type)

    @classmethod
    def apply_template_data(
        cls, template: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply context data to template placeholders.

        Args:
            template: Template dictionary with placeholders
            context: Context data to fill placeholders

        Returns:
            Template with placeholders replaced by actual data
        """
        import copy

        # Deep copy to avoid modifying original template
        filled_template = copy.deepcopy(template)

        def replace_placeholders(obj):
            if isinstance(obj, str):
                for key, value in context.items():
                    placeholder = f"{{{{{key}}}}}"
                    if placeholder in obj:
                        obj = obj.replace(placeholder, str(value))
                return obj
            elif isinstance(obj, dict):
                return {k: replace_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholders(item) for item in obj]
            else:
                return obj

        return replace_placeholders(filled_template)

    @classmethod
    def transform_to_frontend(
        cls,
        session_id: str,
        agent_response: dict[str, Any],
        completion_percentage: float | None = None,
    ) -> dict[str, Any]:
        """
        Transform internal agent response to clean frontend structure with JSON templates.

        Uses JSON templates for rich UX instead of generic completion_percentage responses.
        Templates are loaded from config/ux/ux_templates/ directory.

        Frontend gets structured responses based on message type:
        - help_response: Interactive help with capabilities
        - clarification_request: Structured clarification forms
        - progress_update: Rich progress indicators
        - task_complete: Completion celebration with next steps
        - error_message: User-friendly error handling
        - strategy_response: Strategic recommendations
        - email_generation: Email preview with editing capabilities

        Args:
            session_id: Session identifier
            agent_response: Internal agent response with mixed metadata
            completion_percentage: Override completion percentage (legacy fallback)

        Returns:
            Clean frontend response structure with template-based UX
        """

        # Ensure templates are loaded
        cls.load_templates()

        # Extract message type for template selection
        message_type = cls.extract_message_type(agent_response)

        # Build context for template rendering
        context = cls._build_template_context(
            session_id, agent_response, completion_percentage
        )

        # Try to get template for this message type
        template = cls.get_template(message_type)

        if template:
            # Use template-based response
            filled_template = cls.apply_template_data(template, context)

            # Core response structure with template data - includes ALL required API fields
            frontend_response = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "message": cls.extract_user_message(agent_response),
                "completion_percentage": float(
                    completion_percentage
                    or agent_response.get("completion_percentage", 0.0)
                ),
                "message_type": message_type,
                "source": cls.extract_source_agent(agent_response),
                "template_response": filled_template,
                "use_template": True,
            }

            # Add template-specific fields
            if "ui_structure" in filled_template:
                frontend_response["ui_structure"] = filled_template["ui_structure"]

            # Add optional fields if available
            suggestions = agent_response.get("suggestions", [])
            if suggestions:
                frontend_response["suggestions"] = suggestions

            if "requires_input" in agent_response:
                frontend_response["requires_input"] = agent_response.get(
                    "requires_input", True
                )

        else:
            # Fallback to legacy structure if no template found
            logger.warning(f"No template found for message type: {message_type}")

            # Extract user-facing message content
            user_message = cls.extract_user_message(agent_response)

            # Determine completion percentage (legacy fallback)
            if completion_percentage is None:
                completion_percentage = agent_response.get("completion_percentage", 0.0)

            # Extract suggestions if available
            suggestions = agent_response.get("suggestions", [])

            # Determine if user input is required
            requires_input = agent_response.get("requires_input", True)

            # Extract source agent information
            source = cls.extract_source_agent(agent_response)

            frontend_response = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "message": user_message,
                "completion_percentage": float(completion_percentage),
                "message_type": message_type,
                "source": source,
                "use_template": False,
            }

            # Add optional fields only if they have meaningful content
            if suggestions:
                frontend_response["suggestions"] = suggestions

            if "requires_input" in agent_response:
                frontend_response["requires_input"] = requires_input

        logger.info(
            f"Transformed response for session {session_id}: {message_type} (template: {template is not None})"
        )
        return frontend_response

    @classmethod
    def _build_template_context(
        cls,
        session_id: str,
        agent_response: dict[str, Any],
        completion_percentage: float | None,
    ) -> dict[str, Any]:
        """
        Build context data for template rendering.

        Args:
            session_id: Session identifier
            agent_response: Internal agent response
            completion_percentage: Progress indicator

        Returns:
            Context dictionary for template placeholders
        """

        # Base context data
        context = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "completion_percentage": float(
                completion_percentage
                or agent_response.get("completion_percentage", 0.0)
            ),
            "message_type": cls.extract_message_type(agent_response),
            "source": cls.extract_source_agent(agent_response),
            "user_message": cls.extract_user_message(agent_response),
        }

        # Add email-specific context if available
        if "email_data" in agent_response:
            email_data = agent_response["email_data"]
            context.update(
                {
                    "email_subject": email_data.get("subject", ""),
                    "email_recipients": email_data.get("recipients", ""),
                    "email_content": email_data.get("content", ""),
                    "email_preview": email_data.get("preview", ""),
                    "email_count": email_data.get("count", 1),
                    "email_body": email_data.get("body", ""),
                }
            )

        # Add strategy context
        if "strategy_data" in agent_response:
            strategy_data = agent_response["strategy_data"]
            context.update(
                {
                    "email_type": strategy_data.get("email_type", ""),
                    "recommendation_1": (
                        strategy_data.get("recommendations", [""])[0]
                        if strategy_data.get("recommendations")
                        else ""
                    ),
                    "recommendation_2": (
                        strategy_data.get("recommendations", [""])[1]
                        if len(strategy_data.get("recommendations", [])) > 1
                        else ""
                    ),
                    "recommendation_3": (
                        strategy_data.get("recommendations", [""])[2]
                        if len(strategy_data.get("recommendations", [])) > 2
                        else ""
                    ),
                    "tone": strategy_data.get("tone", ""),
                    "tone_reasoning": strategy_data.get("tone_reasoning", ""),
                    "optimal_timing": strategy_data.get("timing", ""),
                    "timing_reasoning": strategy_data.get("timing_reasoning", ""),
                    "section_1": (
                        strategy_data.get("sections", [""])[0]
                        if strategy_data.get("sections")
                        else ""
                    ),
                    "section_2": (
                        strategy_data.get("sections", [""])[1]
                        if len(strategy_data.get("sections", [])) > 1
                        else ""
                    ),
                    "section_3": (
                        strategy_data.get("sections", [""])[2]
                        if len(strategy_data.get("sections", [])) > 2
                        else ""
                    ),
                }
            )

        # Add error context
        if "error" in agent_response or "error_type" in agent_response:
            context.update(
                {
                    "error_type": agent_response.get("error_type", "Unknown Error"),
                    "error_message": agent_response.get(
                        "error_message", "An unexpected error occurred"
                    ),
                    "technical_error": str(agent_response.get("error", "")),
                }
            )

        # Add progress context
        if "current_stage" in agent_response:
            context["current_stage"] = agent_response["current_stage"]

        return context

    @staticmethod
    def extract_user_message(agent_response: dict[str, Any]) -> str:
        """
        Extract user-facing message content from agent response.

        Looks for user content in various response formats and provides
        sensible fallbacks for different agent response structures.

        Args:
            agent_response: Internal agent response

        Returns:
            User-facing message content
        """

        # Priority order for extracting user message content
        message_fields = [
            "user_message",  # Preferred field for user content
            "message",  # Common message field
            "content",  # Generic content field
            "response_text",  # Alternative response field
            "output",  # Agent output field
            "result",  # Result field
        ]

        for field in message_fields:
            if field in agent_response and agent_response[field]:
                content = agent_response[field]
                if isinstance(content, str) and content.strip():
                    return content.strip()

        # Check if this is a help response with capability guidance
        if (
            agent_response.get("type") == "help_response"
            or agent_response.get("message_type") == "help_response"
        ):
            return agent_response.get(
                "help_content", "Here's what I can help you with..."
            )

        # Check if this is a route_to_workflow (silent handoff) - no user message should be generated
        # This follows LangGraph conditional routing pattern where agent-to-agent routing is silent
        if agent_response.get("message_type") == "route_to_workflow":
            return None  # No user message for silent handoff

        # Check for structured responses
        if "structured_output" in agent_response:
            structured = agent_response["structured_output"]
            if isinstance(structured, dict):
                return structured.get("user_message", structured.get("message", ""))

        # Fallback based on response type
        response_type = agent_response.get(
            "type", agent_response.get("message_type", "")
        )

        fallback_messages = {
            "help_response": "I can help you with various tasks. Let me know what you'd like to accomplish.",
            "clarification": "I need a bit more information to help you effectively.",
            "error": "I encountered an issue processing your request. Let me try a different approach.",
            "progress": "I'm working on your request...",
            "complete": "I've completed processing your request.",
        }

        if response_type in fallback_messages:
            return fallback_messages[response_type]

        # Final fallback
        logger.warning(
            f"No user message found in agent response: {list(agent_response.keys())}"
        )
        return "I'm processing your request..."

    @staticmethod
    def extract_message_type(agent_response: dict[str, Any]) -> str:
        """
        Extract message type for UI rendering hints.

        Args:
            agent_response: Internal agent response

        Returns:
            Message type for frontend UI rendering
        """

        # Check explicit message_type field
        if "message_type" in agent_response:
            return agent_response["message_type"]

        # Check type field
        if "type" in agent_response:
            response_type = agent_response["type"]

            # Map internal types to frontend types
            type_mapping = {
                "help_response": "help_response",
                "clarification": "clarification_request",
                "error": "error_message",
                "complete": "task_complete",
                "progress": "progress_update",
                "requirements": "requirements_request",
                "strategy": "strategy_response",
                "email": "email_generation",
            }

            return type_mapping.get(response_type, "response")

        # Check for help indicators
        if any(
            key in agent_response
            for key in ["help_content", "capabilities", "capability_guidance"]
        ):
            return "help_response"

        # Check for clarification indicators
        if any(
            key in agent_response
            for key in ["clarification_reason", "needs_clarification"]
        ):
            return "clarification_request"

        # Check for error indicators
        if any(key in agent_response for key in ["error", "error_message", "failure"]):
            return "error_message"

        # Check completion indicators
        completion_pct = agent_response.get("completion_percentage", 0)
        if completion_pct >= 100:
            return "task_complete"
        elif completion_pct > 0:
            return "progress_update"

        # Default to generic response
        return "response"

    @staticmethod
    def extract_source_agent(agent_response: dict[str, Any]) -> str:
        """
        Extract source agent name from agent response.

        Args:
            agent_response: Internal agent response

        Returns:
            Name of the agent/system that produced the response
        """

        # Check explicit source field
        if "source" in agent_response:
            return agent_response["source"]

        # Check agent_name field
        if "agent_name" in agent_response:
            return agent_response["agent_name"]

        # Check for executing_agent field
        if "executing_agent" in agent_response:
            return agent_response["executing_agent"]

        # Check metadata for agent information
        if "metadata" in agent_response:
            metadata = agent_response["metadata"]
            if isinstance(metadata, dict):
                for field in ["agent_name", "source", "executing_agent", "from_agent"]:
                    if field in metadata and metadata[field]:
                        return metadata[field]

        # Check based on response type
        response_type = agent_response.get(
            "type", agent_response.get("message_type", "")
        )

        agent_type_mapping = {
            "help_response": "intent_classifier",
            "clarification": "requirements_collector",
            "requirements": "requirements_collector",
            "strategy": "strategy_generator",
            "email": "email_generator",
            "error": "system",
        }

        if response_type in agent_type_mapping:
            return agent_type_mapping[response_type]

        # Final fallback
        return "system"

    @classmethod
    def log_internal_execution(
        cls,
        agent_response: dict[str, Any],
        session_id: str,
        execution_time_ms: float,
        agent_name: str = "unknown",
    ) -> None:
        """
        Log internal execution details for developer debugging.

        This captures the full agent response with all internal metadata
        for backend debugging while keeping frontend responses clean.

        Args:
            agent_response: Complete internal agent response
            session_id: Session identifier
            execution_time_ms: Execution time in milliseconds
            agent_name: Name of the executing agent
        """

        log_data = {
            "agent_name": agent_name,
            "session_id": session_id,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now().isoformat(),
            "internal_response": agent_response,
            "user_message_extracted": cls.extract_user_message(agent_response),
            "message_type_extracted": cls.extract_message_type(agent_response),
        }

        logger.info(
            f"Agent execution: {agent_name} | Session: {session_id} | Time: {execution_time_ms:.2f}ms"
        )
    logger.info(f"Full agent response: {log_data}")


if __name__ == "__main__":
    """
    Validation function for response transformer with template integration.
    Tests template loading and response transformation with real data.
    """
    import sys

    # Track validation failures
    validation_failures = []
    total_tests = 0

    print("Validating Response Transformer with Template Integration...")

    # Test 1: Template Loading
    total_tests += 1
    try:
        APIResponseTransformer.load_templates()
        if not APIResponseTransformer._templates_loaded:
            validation_failures.append(
                "Template loading failed - templates not marked as loaded"
            )
        elif len(APIResponseTransformer._templates_cache) == 0:
            validation_failures.append("Template loading failed - no templates loaded")
        else:
            print(
                f"Template loading successful - {len(APIResponseTransformer._templates_cache)} templates loaded"
            )
    except Exception as e:
        validation_failures.append(f"Template loading failed with exception: {e}")

    # Test 2: Help Response Template
    total_tests += 1
    help_template = APIResponseTransformer.get_template("help_response")
    if not help_template:
        validation_failures.append("Help response template not found")
    else:
        print("Help response template loaded successfully")

    # Test 3: Progress Update Template
    total_tests += 1
    progress_template = APIResponseTransformer.get_template("progress_update")
    if not progress_template:
        validation_failures.append("Progress update template not found")
    else:
        print("Progress update template loaded successfully")

    # Test 4: Template-based Response Transformation
    total_tests += 1
    try:
        test_response = {
            "type": "help_response",
            "user_message": "How can I help you today?",
            "capabilities": ["email writing", "batch processing", "strategy advice"],
        }

        transformed = APIResponseTransformer.transform_to_frontend(
            session_id="test-session-123", agent_response=test_response
        )

        if transformed.get("use_template"):
            print("Template-based transformation successful")
            if "template_response" in transformed:
                print("   - Template response structure present")
            if "ui_structure" in transformed:
                print("   - UI structure present")
        else:
            print("Fallback to legacy structure (may be expected if templates missing)")

    except Exception as e:
        validation_failures.append(f"Template transformation failed: {e}")

    # Test 5: Legacy Fallback
    total_tests += 1
    try:
        test_response_legacy = {
            "message": "Test message",
            "completion_percentage": 75.0,
            "type": "unknown_type",
        }

        transformed_legacy = APIResponseTransformer.transform_to_frontend(
            session_id="test-session-456", agent_response=test_response_legacy
        )

        if not transformed_legacy.get("use_template"):
            print("Legacy fallback working correctly")
        else:
            validation_failures.append("Unexpected template usage for unknown type")

    except Exception as e:
        validation_failures.append(f"Legacy fallback failed: {e}")

    # Test 6: Context Building
    total_tests += 1
    try:
        test_context_response = {
            "type": "email_generation",
            "email_data": {
                "subject": "Test Subject",
                "recipients": "test@example.com",
                "content": "Test email content",
            },
        }

        context = APIResponseTransformer._build_template_context(
            session_id="test-session-789",
            agent_response=test_context_response,
            completion_percentage=100.0,
        )

        if context.get("email_subject") == "Test Subject":
            print("Context building for email data successful")
        else:
            validation_failures.append(
                "Context building failed - email data not extracted"
            )

    except Exception as e:
        validation_failures.append(f"Context building failed: {e}")

    # Final validation result
    if validation_failures:
        print(
            f"\nVALIDATION FAILED - {len(validation_failures)} of {total_tests} tests failed:"
        )
        for failure in validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"\nVALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Response transformer with template integration is validated")

        # Show available templates
        print("\nAvailable Templates:")
        for template_type in sorted(APIResponseTransformer._templates_cache.keys()):
            template = APIResponseTransformer._templates_cache[template_type]
            print(f"   - {template_type}: {template.get('title', 'No title')}")

        sys.exit(0)
