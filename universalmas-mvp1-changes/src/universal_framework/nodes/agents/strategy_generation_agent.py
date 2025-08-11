"""Strategy generation agent combining enterprise features with performance optimization."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import Any

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from universal_framework.compliance import EnterpriseAuditManager, PrivacySafeLogger
from universal_framework.config.feature_flags import feature_flags

# Conditionally import LangSmith tracing only if enabled
if not feature_flags.is_safe_mode() and feature_flags.is_enabled("LANGSMITH_TRACING"):
    try:
        from langsmith import traceable

        _tracing_available = True
    except ImportError:
        _tracing_available = False

        # No-op decorator for when LangSmith is not available
        def traceable(*args, **kwargs):
            def decorator(func):
                return func

            return decorator if args and callable(args[0]) else decorator

else:
    _tracing_available = False

    # No-op decorator for safe mode
    def traceable(*args, **kwargs):
        def decorator(func):
            return func

        return decorator if args and callable(args[0]) else decorator


from universal_framework.contracts import (
    LLMConnectionError,
    PerformanceTimeoutError,
    StrategyValidationError,
)
from universal_framework.contracts.state import (
    ConflictAnalysis,
    EmailRequirements,
    EmailStrategy,
    UniversalWorkflowState,
    WorkflowPhase,
)
from universal_framework.llm.providers import (
    LLMConfig,
    LLMProvider,
    create_default_provider,
)
from universal_framework.observability import UniversalFrameworkLogger
from universal_framework.utils.template_selector import EmailTemplateSelector

logger = UniversalFrameworkLogger("strategy_generator")


class StrategyGenerationError(Exception):
    """Exception raised when strategy generation fails."""

    pass


class StrategyGenerationAgent:
    """
    Unified strategy generation agent combining enterprise features with performance optimization.

    LangGraph-aligned: Single responsibility for strategy generation.
    Supports both comprehensive and performance modes with enterprise audit features.
    The graph handles orchestration via conditional edges, not this node.

    Consolidates the functionality from both StrategyGenerator and StrategyGeneratorAgent
    into a single, well-designed class that supports:
    - LangChain agent executor with tools
    - Performance-optimized generation (<400ms)
    - Enterprise audit and compliance
    - Conflict detection and resolution
    - Fallback strategy generation
    """

    def __init__(
        self,
        *,
        llm_provider: LLMProvider | None = None,
        llm_config: LLMConfig | None = None,
        enable_agent_executor: bool = True,
        performance_mode: bool = False,
    ) -> None:
        """
        Initialize unified strategy generator.

        Args:
            llm_provider: LLM provider for comprehensive features
            llm_config: Direct LLM config for performance mode
            enable_agent_executor: Whether to enable LangChain agent executor
            performance_mode: Enable performance optimizations for <400ms generation
        """
        # Initialize LLM - prefer provider over config
        if llm_provider:
            self.llm_provider = llm_provider
            self.llm = llm_provider.create_agent_llm()
        elif llm_config:
            self.llm_provider = None
            self.llm = self._initialize_performance_llm(llm_config)
        else:
            self.llm_provider = create_default_provider()
            self.llm = self.llm_provider.create_agent_llm()

        # Configuration
        self.performance_mode = performance_mode or (llm_config is not None)
        self.enable_agent_executor = enable_agent_executor and not self.performance_mode

        # Components
        self.logger = UniversalFrameworkLogger("strategy_generator")

        if feature_flags.is_enabled("ENTERPRISE_FEATURES"):
            from ...observability.enterprise_langsmith import EnterpriseLangSmithConfig

            langsmith_config = EnterpriseLangSmithConfig()
            self.audit_manager = EnterpriseAuditManager(
                PrivacySafeLogger(), langsmith_config
            )
        else:
            # Safe mode - use minimal audit interface
            from ...compliance.safe_mode import SafeModeAuditManager

            self.audit_manager = SafeModeAuditManager()

        self.template_selector = EmailTemplateSelector()

        # Performance settings
        self.max_generation_time_seconds = 0.4 if self.performance_mode else 30.0
        self.fallback_timeout_seconds = 0.1
        self.max_retries = 1 if self.performance_mode else 3

        # Initialize agent executor if enabled
        if self.enable_agent_executor:
            self.strategy_templates = self._load_strategy_templates()
            self.tools = self._create_strategy_tools()
            self.agent_executor = self._create_agent_executor()
        else:
            self.strategy_templates = {}
            self.tools = []
            self.agent_executor = None

    def _initialize_performance_llm(self, llm_config: LLMConfig) -> ChatOpenAI:
        """Initialize LLM optimized for <400ms performance."""
        try:
            # Build ChatOpenAI with project-based authentication
            llm_kwargs = {
                "api_key": llm_config.openai_api_key,
                "model": "gpt-3.5-turbo",
                "temperature": 0.3,
                "max_tokens": 300,
                "request_timeout": 0.3,
                "max_retries": 1,
                "streaming": False,
            }

            # Add organization for project-scoped API keys
            if llm_config.openai_organization:
                llm_kwargs["organization"] = llm_config.openai_organization

            # Project ID should be passed via model_kwargs
            if llm_config.openai_project:
                llm_kwargs["model_kwargs"] = {"project": llm_config.openai_project}

            return ChatOpenAI(**llm_kwargs)
        except (ConnectionError, TimeoutError, ValueError) as exc:
            self.logger.error(
                "Performance LLM initialization failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise StrategyGenerationError(
                f"Strategy generator LLM initialization failed: {exc}"
            ) from exc

    def _create_strategy_tools(self) -> list[Tool]:
        """Create LangChain tools for strategy generation."""
        return [
            Tool(
                name="conflict_detector",
                description=(
                    "Detect conflicts between strategy and preferences. Input: "
                    "JSON with 'strategy' and 'preferences'."
                ),
                func=self._tool_detect_conflicts,
            ),
            Tool(
                name="template_selector",
                description=(
                    "Select email template based on email type. Input: JSON with"
                    " 'email_type'."
                ),
                func=self._tool_select_template,
            ),
            Tool(
                name="strategy_validator",
                description=(
                    "Validate strategy completeness and compliance. Input: "
                    "strategy JSON."
                ),
                func=self._tool_validate_strategy,
            ),
        ]

    def _create_agent_executor(self) -> AgentExecutor:
        """Create LangChain agent executor with strategy tools."""
        llm = self.llm
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are an enterprise email strategy expert."),
                ("user", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )
        agent = create_openai_tools_agent(llm, self.tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            max_iterations=3,
            early_stopping_method="generate",
        )

    @traceable(
        name="unified_strategy_generator_execution",
        tags=["email_workflow", "strategy_analysis"],
        metadata=lambda state: {
            "session_id": getattr(state, "session_id", "unknown"),
            "user_id": getattr(state, "user_id", "unknown"),
            "workflow_phase": getattr(
                state, "workflow_phase", WorkflowPhase.INITIALIZATION
            ).value,
            "email_type": getattr(
                getattr(state, "email_requirements", None),
                "email_type",
                "unknown",
            ),
            "has_requirements": getattr(state, "email_requirements", None) is not None,
            "performance_mode": "performance_mode",
            "agent_executor_enabled": "enable_agent_executor",
        },
    )
    async def execute(self, state: UniversalWorkflowState) -> UniversalWorkflowState:
        """Execute strategy generation with unified approach - LangGraph aligned."""
        await self._validate_enterprise_prerequisites(state)

        start_time = time.perf_counter()

        # Defensive programming for LangGraph state conversion
        email_requirements = (
            state.email_requirements
            if hasattr(state, "email_requirements")
            else state.get("email_requirements")
        )
        context_data = (
            state.context_data
            if hasattr(state, "context_data")
            else state.get("context_data", {})
        )

        if self.performance_mode:
            # Performance-optimized path
            strategy = await self._generate_strategy_performance_mode(
                email_requirements
            )
        else:
            # Comprehensive path with agent executor
            strategy, llm_duration, parsing_duration = (
                await self._generate_strategy_comprehensive(
                    email_requirements, context_data
                )
            )

        # Common conflict detection and state update
        conflicts = await self._detect_conflicts(
            strategy,
            email_requirements,
            context_data.get("user_preferences", {}),
        )

        updated = state.update_strategy(strategy, conflicts)

        # Performance metrics
        total_time = time.perf_counter() - start_time
        self._collect_performance_metrics(start_time, conflicts, total_time)

        # Defensive programming for LangGraph state conversion
        session_id = (
            state.session_id
            if hasattr(state, "session_id")
            else state.get("session_id", "unknown")
        )

        self.logger.info(
            "unified_strategy_generation_completed",
            session_id=session_id,
            performance_mode=self.performance_mode,
            execution_time_ms=total_time * 1000,
            strategy_confidence=strategy.confidence_score,
            conflicts_detected=len(conflicts) if conflicts else 0,
        )

        return updated

    # Backward compatibility method - redirect to execute for UniversalWorkflowState
    async def generate_strategy(self, requirements: EmailRequirements) -> EmailStrategy:
        """Generate strategy from requirements (backward compatibility)."""
        if self.performance_mode:
            return await self._generate_strategy_performance_mode(requirements)
        else:
            strategy, _, _ = await self._generate_strategy_comprehensive(
                requirements, {}
            )
            return strategy

    async def _generate_strategy_performance_mode(
        self, requirements: EmailRequirements
    ) -> EmailStrategy:
        """Generate strategy in performance mode (<400ms)."""
        start_time = datetime.now()

        try:
            strategy = await self._generate_strategy_with_llm(requirements)
            conflicts = await self._detect_conflicts_fast(strategy, requirements)
            if conflicts:
                strategy = await self._resolve_conflicts_fast(
                    strategy, requirements, conflicts
                )
            strategy = await self._optimize_strategy(strategy)
            self._validate_strategy(strategy, requirements)

            execution_time = (datetime.now() - start_time).total_seconds()
            self.audit_manager.track_agent_execution(
                "strategy_generator",
                getattr(requirements, "session_id", "unknown"),
                {
                    "use_case": getattr(requirements, "use_case", "generic"),
                    "start_time": start_time.isoformat(),
                    "performance_mode": True,
                },
                {"execution_time": execution_time},
            )
            return strategy

        except (PerformanceTimeoutError, StrategyGenerationError) as exc:
            self.logger.error(
                "Performance strategy generation failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            try:
                return await self._fallback_strategy_generation(requirements)
            except (
                StrategyGenerationError,
                ValidationError,
                TimeoutError,
            ) as fallback_exc:
                raise StrategyGenerationError(
                    f"Strategy generation failed: {exc}. Fallback also failed: {fallback_exc}"
                ) from exc
        except (ConnectionError, TimeoutError) as exc:
            self.logger.error(
                "LLM connection failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise LLMConnectionError(
                f"Strategy generation LLM connection failed: {exc}"
            ) from exc
        except ValidationError as exc:
            self.logger.error(
                "Strategy validation failed",
                error=str(exc),
                validation_errors=exc.errors() if hasattr(exc, "errors") else [],
            )
            raise StrategyValidationError(f"Strategy validation failed: {exc}") from exc

    async def _generate_strategy_comprehensive(
        self, requirements: EmailRequirements, context_data: dict[str, Any]
    ) -> tuple[EmailStrategy, float, float]:
        """Generate strategy using comprehensive approach with agent executor."""
        start_time = time.perf_counter()

        # Use agent executor if available
        if self.agent_executor:
            strategy = await self._generate_with_agent_executor(
                requirements, context_data
            )
        else:
            strategy = await self._generate_strategy_with_llm(requirements)

        llm_duration = time.perf_counter() - start_time

        # Parse and validate
        parse_start = time.perf_counter()
        if not isinstance(strategy, EmailStrategy):
            strategy = EmailStrategy.model_validate(strategy)
        parsing_duration = time.perf_counter() - parse_start

        return strategy, llm_duration, parsing_duration

    async def _generate_with_agent_executor(
        self, requirements: EmailRequirements, context_data: dict[str, Any]
    ) -> EmailStrategy:
        """Generate strategy using LangChain agent executor."""
        if not self.agent_executor:
            raise StrategyGenerationError("Agent executor not available")

        try:
            input_data = {
                "requirements": requirements.model_dump(),
                "context": context_data,
                "template_type": getattr(requirements, "email_type", "general"),
            }

            result = await self.agent_executor.ainvoke(
                {"input": json.dumps(input_data)}
            )

            # Extract strategy from agent result
            if isinstance(result.get("output"), dict):
                return EmailStrategy.model_validate(result["output"])
            else:
                # Parse text output
                return await self._parse_agent_output(result.get("output", ""))

        except Exception as exc:
            self.logger.warning(
                "Agent executor failed, falling back to direct LLM", error=str(exc)
            )
            return await self._generate_strategy_with_llm(requirements)

    async def _generate_strategy_with_llm(
        self, requirements: EmailRequirements
    ) -> EmailStrategy:
        """Generate strategy with direct LLM call."""
        prompt_template = self._create_strategy_prompt_template(
            getattr(requirements, "use_case", "generic")
        )
        parser = PydanticOutputParser(pydantic_object=EmailStrategy)
        chain = prompt_template | self.llm | parser

        try:
            result = await asyncio.wait_for(
                chain.ainvoke(
                    {
                        "requirements": (
                            self._optimize_requirements_for_speed(requirements)
                            if self.performance_mode
                            else requirements.model_dump()
                        ),
                        "use_case": getattr(requirements, "use_case", "generic"),
                        "format_instructions": parser.get_format_instructions(),
                    }
                ),
                timeout=self.max_generation_time_seconds,
            )
            return result
        except TimeoutError as exc:
            self.logger.warning(
                "Strategy generation timeout, using fallback",
                timeout_seconds=self.max_generation_time_seconds,
            )
            raise PerformanceTimeoutError(
                f"Strategy generation exceeded {self.max_generation_time_seconds}s timeout"
            ) from exc

    # Helper methods
    def _load_strategy_templates(self) -> dict[str, Any]:
        """Load strategy templates for different use cases."""
        return {
            "announcement": {
                "tone": "informative",
                "structure": ["headline", "details", "next_steps"],
                "approach": "clear_communication",
            },
            "request": {
                "tone": "polite",
                "structure": ["context", "request", "rationale", "call_to_action"],
                "approach": "persuasive",
            },
            "update": {
                "tone": "neutral",
                "structure": ["summary", "changes", "impact"],
                "approach": "factual",
            },
        }

    def _create_strategy_prompt_template(self, use_case: str) -> ChatPromptTemplate:
        """Create prompt template for strategy generation."""
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f"""You are an expert email strategy consultant. Generate a comprehensive email strategy for {use_case} use case.

            Focus on:
            - Clear overall approach
            - Appropriate tone and messaging
            - Effective structure
            - Key messages that resonate
            - Target audience considerations

            Respond only with valid JSON matching the EmailStrategy schema.""",
                ),
                (
                    "user",
                    """Requirements: {requirements}
            Use case: {use_case}

            {format_instructions}""",
                ),
            ]
        )

    def _optimize_requirements_for_speed(
        self, requirements: EmailRequirements
    ) -> dict[str, Any]:
        """Optimize requirements for faster processing."""
        return {
            "purpose": requirements.purpose[:100] if requirements.purpose else "",
            "email_type": requirements.email_type,
            "audience": requirements.audience[:3] if requirements.audience else [],
            "tone": requirements.tone,
            "key_messages": (
                requirements.key_messages[:3] if requirements.key_messages else []
            ),
        }

    async def _parse_agent_output(self, output: str) -> EmailStrategy:
        """Parse agent executor output into EmailStrategy."""
        try:
            # Try to extract JSON from the output
            import re

            json_match = re.search(r"\{.*\}", output, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                return EmailStrategy.model_validate(data)
            else:
                # Fallback: create strategy from text
                return EmailStrategy(
                    overall_approach=output[:200],
                    tone_strategy="professional",
                    structure_strategy=["introduction", "main_content", "conclusion"],
                    messaging_strategy={"primary": "extracted_content"},
                    personalization_strategy={},
                    estimated_impact="medium",
                    confidence_score=0.7,
                    target_audience="general",
                    tone="professional",
                    approach=output[:100],
                    key_messages=[output[:100]],
                    timing_considerations="immediate",
                    success_metrics="engagement",
                )
        except Exception as exc:
            self.logger.error("Failed to parse agent output", error=str(exc))
            raise StrategyGenerationError(
                f"Could not parse agent output: {exc}"
            ) from exc

    async def _detect_conflicts_fast(
        self, strategy: EmailStrategy, requirements: EmailRequirements
    ) -> list[str]:
        """Fast conflict detection for performance mode."""
        conflicts = []

        # Quick tone check
        if strategy.tone != requirements.tone:
            conflicts.append(
                f"Tone mismatch: strategy uses {strategy.tone}, required {requirements.tone}"
            )

        # Quick audience check
        if strategy.target_audience and requirements.audience:
            strategy_audience = strategy.target_audience.lower()
            required_audiences = [aud.lower() for aud in requirements.audience]
            if not any(aud in strategy_audience for aud in required_audiences):
                conflicts.append("Target audience mismatch")

        return conflicts

    async def _resolve_conflicts_fast(
        self,
        strategy: EmailStrategy,
        requirements: EmailRequirements,
        conflicts: list[str],
    ) -> EmailStrategy:
        """Fast conflict resolution for performance mode."""
        # Simple resolution - update strategy with requirements
        updates = {}

        if "tone mismatch" in str(conflicts).lower():
            updates["tone"] = requirements.tone
            updates["tone_strategy"] = requirements.tone

        if "audience mismatch" in str(conflicts).lower():
            updates["target_audience"] = ", ".join(requirements.audience[:2])

        if updates:
            return strategy.model_copy(update=updates)

        return strategy

    async def _optimize_strategy(self, strategy: EmailStrategy) -> EmailStrategy:
        """Optimize strategy for better performance."""
        updates = {}

        # Limit key messages to 5 for performance
        if len(strategy.key_messages) > 5:
            updates["key_messages"] = strategy.key_messages[:5]

        # Ensure confidence score is reasonable
        if strategy.confidence_score > 0.95:
            updates["confidence_score"] = 0.9
        elif strategy.confidence_score < 0.1:
            updates["confidence_score"] = 0.3

        if updates:
            return strategy.model_copy(update=updates)

        return strategy

    def _validate_strategy(
        self, strategy: EmailStrategy, requirements: EmailRequirements
    ) -> None:
        """Validate strategy completeness."""
        if not strategy.key_messages:
            raise StrategyGenerationError("Strategy missing key messages")

        if not strategy.overall_approach:
            raise StrategyGenerationError("Strategy missing overall approach")

        if strategy.confidence_score < 0.1:
            raise StrategyGenerationError("Strategy confidence too low")

    async def _fallback_strategy_generation(
        self, requirements: EmailRequirements
    ) -> EmailStrategy:
        """Generate ultra-fast fallback strategy in <100ms."""
        start_time = datetime.now()

        try:
            fallback = EmailStrategy(
                overall_approach=f"Direct communication for {requirements.purpose[:50]}",
                tone_strategy=getattr(requirements, "tone", "professional"),
                structure_strategy=["introduction", "main_content", "conclusion"],
                messaging_strategy={"primary": "key_message"},
                personalization_strategy={},
                estimated_impact="medium",
                confidence_score=0.6,
                target_audience=", ".join(requirements.audience[:2]),
                tone=getattr(requirements, "tone", "professional"),
                approach="Fallback strategy for immediate delivery",
                key_messages=requirements.key_messages[:2],
                timing_considerations="Immediate delivery",
                success_metrics="Basic engagement metrics",
            )

            execution_time = (datetime.now() - start_time).total_seconds()
            if execution_time > self.fallback_timeout_seconds:
                self.logger.warning(
                    "Fallback strategy generation exceeded timeout",
                    execution_time_ms=execution_time * 1000,
                    timeout_ms=self.fallback_timeout_seconds * 1000,
                )

            return fallback
        except ValidationError as exc:
            self.logger.error("Fallback strategy validation failed", error=str(exc))
            return EmailStrategy(
                overall_approach="Minimal fallback strategy",
                tone_strategy="professional",
                structure_strategy=[],
                messaging_strategy={},
                personalization_strategy={},
                estimated_impact="low",
                confidence_score=0.3,
                target_audience="general",
                tone="professional",
                approach="Emergency fallback",
                key_messages=["Important communication"],
                timing_considerations="Immediate",
                success_metrics="Delivery confirmation",
            )

    # Tool methods for LangChain agent executor
    def _tool_detect_conflicts(self, tool_input: str) -> str:
        """Tool for detecting conflicts."""
        try:
            data = json.loads(tool_input)
            strategy = data.get("strategy", {})
            preferences = data.get("preferences", {})

            conflicts = []
            if strategy.get("tone") != preferences.get("tone"):
                conflicts.append("tone_mismatch")

            return json.dumps({"conflicts": conflicts})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _tool_select_template(self, tool_input: str) -> str:
        """Tool for selecting templates."""
        try:
            data = json.loads(tool_input)
            email_type = data.get("email_type", "general")
            template = self.template_selector.select_template(email_type)
            return json.dumps({"template": template})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _tool_validate_strategy(self, tool_input: str) -> str:
        """Tool for validating strategies."""
        try:
            data = json.loads(tool_input)
            EmailStrategy.model_validate(data)
            return json.dumps({"valid": True})
        except ValidationError:
            return json.dumps({"valid": False})

    # Enterprise prerequisite validation
    async def _validate_enterprise_prerequisites(
        self, state: UniversalWorkflowState
    ) -> None:
        """Validate enterprise prerequisites before generation."""
        # Defensive programming for LangGraph state conversion
        email_requirements = (
            state.email_requirements
            if hasattr(state, "email_requirements")
            else state.get("email_requirements")
        )
        session_id = (
            state.session_id
            if hasattr(state, "session_id")
            else state.get("session_id")
        )

        if not email_requirements:
            raise StrategyValidationError("Email requirements not found in state")

        if not session_id:
            raise StrategyValidationError("Session ID required for enterprise audit")

    # Conflict detection
    async def _detect_conflicts(
        self,
        strategy: EmailStrategy,
        requirements: EmailRequirements,
        user_preferences: dict[str, Any],
    ) -> list[ConflictAnalysis]:
        """Detect conflicts between strategy and requirements/preferences."""
        conflicts = []

        # Tone conflicts
        if strategy.tone != requirements.tone:
            conflicts.append(
                ConflictAnalysis(
                    conflict_type="tone_mismatch",
                    description=f"Strategy tone '{strategy.tone}' differs from required '{requirements.tone}'",
                    severity="medium",
                    resolution_suggestion=f"Adjust strategy tone to '{requirements.tone}'",
                )
            )

        # Audience conflicts
        if strategy.target_audience and requirements.audience:
            strategy_audience = strategy.target_audience.lower()
            required_audiences = [aud.lower() for aud in requirements.audience]
            if not any(aud in strategy_audience for aud in required_audiences):
                conflicts.append(
                    ConflictAnalysis(
                        conflict_type="audience_mismatch",
                        description="Strategy target audience doesn't match requirements",
                        severity="high",
                        resolution_suggestion="Align strategy with required audience",
                    )
                )

        # User preference conflicts
        preferred_tone = user_preferences.get("tone")
        if preferred_tone and strategy.tone != preferred_tone:
            conflicts.append(
                ConflictAnalysis(
                    conflict_type="preference_mismatch",
                    description=f"Strategy tone conflicts with user preference for '{preferred_tone}'",
                    severity="low",
                    resolution_suggestion=f"Consider user preference for '{preferred_tone}' tone",
                )
            )

        return conflicts

    # Performance metrics
    def _collect_performance_metrics(
        self, start_time: float, conflicts: list[ConflictAnalysis], total_time: float
    ) -> dict[str, Any]:
        """Collect performance metrics for monitoring."""
        return {
            "total_execution_time": total_time,
            "conflicts_detected": len(conflicts) if conflicts else 0,
            "performance_mode": self.performance_mode,
            "agent_executor_used": self.enable_agent_executor,
            "timestamp": datetime.now().isoformat(),
        }


# Backward compatibility alias
StrategyGenerator = StrategyGenerationAgent
