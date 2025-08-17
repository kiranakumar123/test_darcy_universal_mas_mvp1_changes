"""Environment-based configuration following modern patterns."""

import os
import tomllib
from pathlib import Path
from typing import Any

from universal_framework.llm.providers import LLMConfig
from universal_framework.observability import UniversalFrameworkLogger

logger = UniversalFrameworkLogger("environment")


def get_config_from_environment() -> LLMConfig | None:
    """Get configuration from environment variables."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("openai_api_key_missing_from_environment")
        return None

    return LLMConfig(
        openai_api_key=api_key,
        model_name=os.getenv("OPENAI_MODEL", "gpt-4.1-nano"),
        temperature=float(os.getenv("TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("MAX_TOKENS", "2000")),
    )


def get_langsmith_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Get LangSmith configuration from environment or TOML."""

    # Import feature flags to check safe mode
    from .feature_flags import feature_flags

    config: dict[str, Any] = {}
    env = os.getenv("ENVIRONMENT", "development")

    possible_paths = [
        Path("config/langsmith.toml"),
        Path("langsmith.toml"),
        Path.cwd() / "config" / "langsmith.toml",
    ]

    config_file = Path(config_path) if config_path else None
    if not config_file:
        for path in possible_paths:
            if path.exists():
                config_file = path
                break

    if config_file and config_file.exists():
        with open(config_file, "rb") as f:
            data = tomllib.load(f)
        base = data.get("langsmith", {})
        config.update(base.get("enterprise", {}))
        env_settings = base.get("environments", {}).get(env, {})
        config.update(env_settings)

    if api_key := os.getenv("LANGSMITH_API_KEY"):
        config["api_key"] = api_key

    if project := os.getenv("LANGCHAIN_PROJECT"):
        config["project"] = project
    else:
        config.setdefault("project", "universal-framework")

    # Only enable LangSmith tracing if safe mode allows and feature flag is enabled
    if (
        config.get("api_key")
        and not feature_flags.is_safe_mode()
        and feature_flags.is_enabled("LANGSMITH_TRACING")
    ):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        logger.info("langsmith_config_detected", project=config["project"])
    elif feature_flags.is_safe_mode():
        # Ensure tracing is disabled in safe mode
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
    logger.info("langsmith_tracing_disabled_safe_mode")

    return config
