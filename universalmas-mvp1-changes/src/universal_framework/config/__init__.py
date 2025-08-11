"""Configuration management for Universal Framework."""

from universal_framework.llm.providers import LLMConfig

from .environment import get_config_from_environment
from .factory import create_compliance_config, create_llm_config
from .toml_loader import get_llm_config_from_toml, load_toml_config


def get_llm_config() -> LLMConfig:
    """Return LLM configuration from available sources."""

    return create_llm_config()


__all__ = [
    "load_toml_config",
    "get_llm_config_from_toml",
    "get_config_from_environment",
    "get_llm_config",
    "create_compliance_config",
]
