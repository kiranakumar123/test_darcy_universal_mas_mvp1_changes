"""TOML configuration loader following modern Python patterns."""

import os
import tomllib
from pathlib import Path
from typing import Any

from universal_framework.llm.providers import LLMConfig
from universal_framework.observability import UniversalFrameworkLogger

logger = UniversalFrameworkLogger("toml_loader")


def load_toml_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load TOML configuration file."""

    if config_path is None:
        # Default config locations
        possible_paths = [
            Path("config/llm.toml"),
            Path("llm.toml"),
            Path.cwd() / "config" / "llm.toml",
        ]

        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break
    else:
        config_path = Path(config_path)

    if not config_path or not config_path.exists():
        logger.warning(
            "toml_config_not_found", searched_paths=[str(p) for p in possible_paths]
        )
        return {}

    try:
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)

        logger.info("toml_config_loaded", config_path=str(config_path))
        return config_data

    except Exception as e:
        logger.error(
            "toml_config_load_failed", error=str(e), config_path=str(config_path)
        )
        return {}


def get_llm_config_from_toml(config_path: Path | str | None = None) -> LLMConfig | None:
    """Get LLM configuration from TOML file with environment variable substitution."""

    config_data = load_toml_config(config_path)
    if not config_data:
        return None

    llm_config = config_data.get("llm", {})
    if not llm_config:
        logger.warning("no_llm_section_in_toml")
        return None

    try:
        # Substitute environment variables
        api_key = llm_config.get("openai_api_key", "")
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]  # Remove ${ and }
            api_key = os.getenv(env_var, "")

        if not api_key:
            logger.warning(
                "openai_api_key_not_found", toml_value=llm_config.get("openai_api_key")
            )
            return None

        return LLMConfig(
            openai_api_key=api_key,
            model_name=llm_config.get("model_name", "gpt-4.1-nano"),
            temperature=float(llm_config.get("temperature", 0.1)),
            max_tokens=int(llm_config.get("max_tokens", 2000)),
        )

    except Exception as e:
        logger.error("llm_config_creation_failed", error=str(e))
        return None
