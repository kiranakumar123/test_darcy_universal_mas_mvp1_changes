"""LLM provider implementations following modern Python patterns."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Self

from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI

from universal_framework.observability import UniversalFrameworkLogger

logger = UniversalFrameworkLogger("llm_providers")

# Load environment variables from .env file if it exists (for local development)
# In production (like Render), environment variables are already set by the platform
try:
    from pathlib import Path

    from dotenv import load_dotenv

    # Only load .env if file exists (local development)
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv()
        logger.info("loaded_env_from_file", env_file=str(env_file))
    else:
        logger.info(
            "using system environment variables", env_status="no_env_file_found"
        )
except ImportError:
    # python-dotenv not installed, use system environment variables only
    logger.info("python-dotenv not available, using system environment variables")


@dataclass(frozen=True)  # Immutable by default
class LLMConfig:
    """LLM configuration from environment and TOML."""

    openai_api_key: str
    model_name: str = (
        "gpt-4.1-nano"  # Cost-effective model with structured output support
    )
    temperature: float = 0.1
    max_tokens: int = 2000
    strategy_timeout_seconds: int = 10
    max_retries: int = 2
    fallback_enabled: bool = True
    # OpenAI Project-based authentication (required for organization accounts)
    openai_organization: str | None = None
    openai_project: str | None = None

    @classmethod
    def from_env(cls) -> Self:
        """Create config from environment variables."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")

        return cls(
            openai_api_key=api_key,
            openai_organization=os.getenv(
                "OPENAI_ORGANIZATION"
            ),  # Load from environment
            openai_project=os.getenv("OPENAI_PROJECT"),  # Load from environment
            model_name=os.getenv(
                "OPENAI_MODEL", "gpt-4.1-nano"
            ),  # Use cost-effective structured output compatible model
            temperature=float(os.getenv("TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("MAX_TOKENS", "2000")),
            strategy_timeout_seconds=int(os.getenv("STRATEGY_TIMEOUT_SECONDS", "10")),
            max_retries=int(os.getenv("MAX_RETRIES", "2")),
            fallback_enabled=os.getenv("FALLBACK_ENABLED", "true") == "true",
        )

    @classmethod
    def from_toml(cls, config_path: Path) -> Self:
        """Create config from TOML file."""
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)

        llm_config = config_data.get("llm", {})
        return cls(
            openai_api_key=llm_config["openai_api_key"],
            model_name=llm_config.get("model_name", "gpt-4.1-nano"),
            temperature=llm_config.get("temperature", 0.1),
            max_tokens=llm_config.get("max_tokens", 2000),
            strategy_timeout_seconds=llm_config.get("strategy_timeout_seconds", 10),
            max_retries=llm_config.get("max_retries", 2),
            fallback_enabled=llm_config.get("fallback_enabled", True),
        )

    def create_agent_llm(self) -> ChatOpenAI:
        """Create ChatOpenAI instance for agent operations."""
        # Build ChatOpenAI with project-based authentication if available
        llm_kwargs = {
            "api_key": self.openai_api_key,
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # Add organization for project-scoped API keys
        if self.openai_organization:
            llm_kwargs["organization"] = self.openai_organization

        return ChatOpenAI(**llm_kwargs)


class LLMProvider(Protocol):
    """Protocol for dependency-injected LLM providers."""

    config: LLMConfig

    def create_agent_llm(self) -> BaseLanguageModel:
        """Return language model instance for agents."""
        ...


class LLMProviderError(Exception):
    """LLM provider specific errors."""

    pass


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider for agent creation."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig.from_env()
        self._llm: BaseLanguageModel | None = None

        logger.info(
            "openai_provider_initialized",
            model=self.config.model_name,
            temperature=self.config.temperature,
        )

    @property
    def llm(self) -> BaseLanguageModel:
        """Get or create ChatOpenAI instance."""
        if self._llm is None:
            try:
                # Build ChatOpenAI kwargs with project-based authentication
                llm_kwargs = {
                    "api_key": self.config.openai_api_key,
                    "model": self.config.model_name,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                }

                # Add organization for project-scoped API keys
                if self.config.openai_organization:
                    llm_kwargs["organization"] = self.config.openai_organization

                self._llm = ChatOpenAI(**llm_kwargs)
                logger.info("openai_provider_initialized", model=self.config.model_name)
            except Exception as e:
                e.add_note(
                    f"Failed to create ChatOpenAI with model {self.config.model_name}"
                )
                raise LLMProviderError("Failed to initialize OpenAI client") from e

        return self._llm

    def create_agent_llm(self) -> BaseLanguageModel:
        """Create LLM specifically configured for agent use."""
        try:
            # Build ChatOpenAI kwargs with project-based authentication
            llm_kwargs = {
                "api_key": self.config.openai_api_key,
                "model": self.config.model_name,
                "temperature": 0.1,  # Lower for consistent agent behavior
                "max_tokens": self.config.max_tokens,
            }

            # Add organization for project-scoped API keys
            if self.config.openai_organization:
                llm_kwargs["organization"] = self.config.openai_organization

            agent_llm = ChatOpenAI(**llm_kwargs)

            logger.info(
                "agent_llm_created",
                model=self.config.model_name,
                temperature=0.1,
                event="openai_provider_initialized",
            )

            return agent_llm

        except Exception as e:
            e.add_note("Failed to create agent-specific LLM instance")
            raise LLMProviderError("Agent LLM creation failed") from e


def create_default_provider() -> OpenAIProvider:
    """Create an OpenAI provider using environment configuration."""
    return OpenAIProvider()
