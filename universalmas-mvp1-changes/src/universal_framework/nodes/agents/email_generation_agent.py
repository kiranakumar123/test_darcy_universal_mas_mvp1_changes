"""LangChain agent for HTML email generation."""

from __future__ import annotations

import json
import time
from typing import Any

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool

from universal_framework.config.feature_flags import feature_flags
from universal_framework.contracts.exceptions import AgentExecutionError
from universal_framework.contracts.state import (
    EmailRequirements,
    EmailStrategy,
    GeneratedEmail,
)
from universal_framework.llm.providers import (
    LLMProvider,
    LLMProviderError,
    create_default_provider,
)

# Removed direct imports - these will be imported conditionally when needed
from universal_framework.utils.template_selector import EmailTemplateSelector

from ...core.logging_foundation import get_safe_logger

logger = get_safe_logger(__name__)


class EmailGenerationAgent:
    """
    LangChain agent for generating final email content.

    Architecture Decisions:
    1. Always returns full GeneratedEmail contract for FSM compliance
    2. Agent-as-LLM-only (tools designed for future extensibility)
    3. Single agent with performance optimization (no separate fast-path agent)
    4. Context parameter guaranteed present (may be empty dict)

    Returns:
        GeneratedEmail: Complete contract with subject, html_content, text_content,
        quality_score, template_used, personalization_applied,
        brand_compliance_score, strategy_applied.
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        enterprise_config: Any | None = None,  # Use Any instead of conditional type
    ) -> None:
        self.llm_provider = llm_provider or create_default_provider()
        self.prompt = self._create_email_prompt()
        self.enterprise_config = enterprise_config
        self.template_selector = EmailTemplateSelector()

    def _create_email_tools(self) -> list[BaseTool]:
        """
        Tools for email generation agent.

        Currently empty - agent-as-LLM-only is sufficient for GENERATION phase.
        Designed for future extensibility without breaking changes.
        Validation tools are used in REVIEW phase, not here.
        """
        return []

    def _create_email_prompt(self) -> ChatPromptTemplate:
        """
        Create structured prompt for email generation.

        Uses JSON output contract for robust FSM/agent compliance.
        Always returns complete GeneratedEmail structure for enterprise audit trails.
        """
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an expert email content generator. Generate professional email content "
                        "and return a JSON object with the following exact structure:\n\n"
                        "{\n"
                        '  "subject": "Email subject line (3-120 characters)",\n'
                        '  "html_content": "Complete HTML email with inline CSS",\n'
                        '  "text_content": "Plain text version of the email",\n'
                        '  "quality_score": 0.95,\n'
                        '  "template_used": "Template type used",\n'
                        '  "personalization_applied": {"key": "value"},\n'
                        '  "brand_compliance_score": 0.90,\n'
                        '  "strategy_applied": "Strategy description"\n'
                        "}\n\n"
                        "Ensure quality_score and brand_compliance_score are between 0.0 and 1.0.\n"
                        "HTML must include proper structure with inline CSS for email clients.\n"
                        "Text content should be readable plain text version."
                    ),
                ),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

    def select_template(self, strategy: EmailStrategy) -> str:
        """Select appropriate template using centralized selector."""
        return self.template_selector.select_template(strategy)

    async def generate_email(
        self,
        strategy: EmailStrategy,
        requirements: EmailRequirements,
        context: dict[str, Any],
    ) -> GeneratedEmail:
        """Generate email with enterprise LangSmith tracing."""

        start = time.perf_counter()

        async def _run() -> GeneratedEmail:
            """
            Generate structured email output using strategy and requirements.

            Args:
                strategy: EmailStrategy with confirmed content and structure
                requirements: EmailRequirements with audience and tone constraints
                context: Additional context data (guaranteed present, may be empty)

            Returns:
                GeneratedEmail: Fully validated, FSM/contract-compliant email output

            Raises:
                LLMProviderError: When LLM provider fails to initialize
                ValueError: When JSON parsing fails or output validation fails
            """
            try:
                llm = self.llm_provider.create_agent_llm()

                # Create agent with minimal tools for performance
                agent = create_openai_functions_agent(
                    llm, self._create_email_tools(), self.prompt
                )

                executor = AgentExecutor(
                    agent=agent,
                    tools=self._create_email_tools(),
                    handle_parsing_errors=True,
                    max_iterations=2,  # Reduced for performance - email generation is straightforward
                    verbose=False,  # Reduce logging overhead in production
                )

                # Prepare structured input with template selection
                template_type = self.select_template(strategy)

                input_data = {
                    "strategy": strategy.model_dump(),
                    "requirements": requirements.model_dump(),
                    "context": context,
                    "template_type": template_type,
                    "personalization": context.get("personalization", {}),
                }

                logger.info(
                    "email_generation_started",
                    template_type=template_type,
                    strategy_subject=strategy.subject,
                    audience_count=len(requirements.audience),
                )

                result = await executor.ainvoke(
                    {"input": json.dumps(input_data, indent=2)}
                )
                output = result.get("output", "")

            except LLMProviderError as e:
                e.add_note("Email generator failed to create LLM instance")
                logger.error("llm_provider_error", error=str(e))
                raise
            except Exception as e:
                logger.error("email_generation_execution_failed", error=str(e))
                raise AgentExecutionError(
                    message=str(e),
                    agent_name="email_generator",
                    execution_phase="generation",
                ) from e

            # Parse and validate JSON output
            try:
                output_text = output if isinstance(output, str) else str(output)

                # Handle potential markdown formatting from LLM
                match output_text:
                    case text if "```json" in text:
                        start_idx = text.find("```json") + 7
                        end_idx = text.find("```", start_idx)
                        output_text = text[start_idx:end_idx].strip()
                    case text if "```" in text:
                        start_idx = text.find("```") + 3
                        end_idx = text.find("```", start_idx)
                        output_text = text[start_idx:end_idx].strip()

                data = json.loads(output_text)

                # Validate required fields and create GeneratedEmail
                generated_email = GeneratedEmail(**data)

                logger.info(
                    "email_generation_completed",
                    subject=generated_email.subject,
                    template_used=generated_email.template_used,
                    quality_score=generated_email.quality_score,
                    html_length=len(generated_email.html_content),
                    text_length=len(generated_email.text_content),
                )

                return generated_email

            except json.JSONDecodeError as e:
                logger.error(
                    "email_json_parse_error",
                    error=str(e),
                    output_text=output_text[:500],
                )
                raise AgentExecutionError(
                    message=f"Failed to parse email generation output as JSON: {e}",
                    agent_name="email_generator",
                    execution_phase="parsing",
                ) from e
            except TypeError as e:
                logger.error("email_validation_error", error=str(e), data=data)
                raise AgentExecutionError(
                    message=f"Email output failed validation: {e}",
                    agent_name="email_generator",
                    execution_phase="validation",
                ) from e

        # Conditional enterprise wrapper based on feature flags
        if feature_flags.is_enabled("LANGSMITH_TRACING") and self.enterprise_config:
            # Import only when needed to avoid safe mode bypass
            from ...observability import enhance_trace_real_agent_execution

            if enhance_trace_real_agent_execution:  # Check if not stubbed
                wrapped = enhance_trace_real_agent_execution(
                    "email_generator",
                    context.get("session_id", "unknown"),
                    self.enterprise_config,
                )(_run)
            else:
                wrapped = _run
        else:
            # Safe mode - no enterprise tracing
            wrapped = _run

        generated_email = await wrapped()
        self._collect_performance_metrics(start, generated_email, strategy)
        return generated_email

    def _collect_performance_metrics(
        self, start: float, email: GeneratedEmail, strategy: EmailStrategy
    ) -> None:
        """Collect email generation performance metrics."""

        total_duration = time.perf_counter() - start

        logger.info(
            "email_generation_performance",
            duration_ms=total_duration * 1000,
            content_length=len(email.html_content) if email.html_content else 0,
            subject_length=len(email.subject) if email.subject else 0,
            template_used=email.template_used,
            generation_method="real_agent",
        )

        if total_duration > 0.5:
            logger.warning(
                "email_generation_performance_warning",
                duration_ms=total_duration * 1000,
                target_ms=500,
                exceeded_by_ms=(total_duration - 0.5) * 1000,
            )

    async def generate_content(
        self,
        strategy: EmailStrategy,
        template_type: str,
        context: dict[str, Any],
    ) -> str:
        """
        Legacy method for backward compatibility with existing node implementation.

        This method provides HTML-only output for the fallback mechanism in the node.
        New code should use generate_email() for full contract compliance.
        """
        try:
            # Create minimal requirements for legacy compatibility
            requirements = EmailRequirements(
                purpose=strategy.overall_approach,
                audience=(
                    strategy.target_audience.split(",")
                    if strategy.target_audience
                    else ["General"]
                ),
                tone=strategy.tone or "professional",
                key_messages=(
                    [strategy.content] if strategy.content else ["Email content"]
                ),
                completeness_score=1.0,
            )

            generated_email = await self.generate_email(strategy, requirements, context)
            return generated_email.html_content

        except Exception as e:
            logger.warning("legacy_generate_content_failed", error=str(e))
            # Return basic HTML fallback for node fallback mechanism
            return f"""
            <html>
            <head>
                <title>{strategy.subject}</title>
                <style>body {{ font-family: Arial, sans-serif; }}</style>
            </head>
            <body>
                <h1>{strategy.subject}</h1>
                <p>{strategy.content}</p>
                <p><strong>{strategy.call_to_action}</strong></p>
            </body>
            </html>
            """
