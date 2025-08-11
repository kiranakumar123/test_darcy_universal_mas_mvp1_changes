"""Configuration factory following priority: TOML > Environment > Defaults."""

import tomllib
from pathlib import Path

from universal_framework.contracts.compliance import ComplianceConfig
from universal_framework.llm.providers import LLMConfig

from ..core.logging_foundation import get_safe_logger
from .environment import get_config_from_environment, get_langsmith_config
from .toml_loader import get_llm_config_from_toml

logger = get_safe_logger(__name__)


def create_llm_config(
    toml_path: Path | str | None = None, prefer_environment: bool = False
) -> LLMConfig:
    """Create LLM configuration with priority: TOML > Environment > Error.

    Args:
        toml_path: Optional path to TOML config file
        prefer_environment: If True, try environment first

    Returns:
        LLMConfig instance

    Raises:
        ValueError: If no valid configuration found
    """

    config_sources = []

    if prefer_environment:
        config_sources = ["environment", "toml"]
    else:
        config_sources = ["toml", "environment"]

    for source in config_sources:
        match source:
            case "toml":
                if config := get_llm_config_from_toml(toml_path):
                    logger.info("llm_config_created", source="toml")
                    return config
            case "environment":
                if config := get_config_from_environment():
                    logger.info("llm_config_created", source="environment")
                    return config

    # If we get here, no config found
    raise ValueError(
        "No valid LLM configuration found. "
        "Set OPENAI_API_KEY environment variable or create config/llm.toml"
    )


def setup_observability() -> dict[str, str]:
    """Setup observability configuration."""

    langsmith_config = get_langsmith_config()

    if langsmith_config.get("api_key"):
        logger.info("observability_enabled", provider="langsmith")
    else:
        logger.info("observability_disabled", reason="no_langsmith_key")

    return langsmith_config


def get_llm_config() -> LLMConfig:
    """Backward-compatible wrapper for create_llm_config."""
    return create_llm_config()


def create_compliance_config(toml_path: Path | str | None = None) -> ComplianceConfig:
    """Create compliance configuration from TOML file."""

    possible_paths = [
        Path("config/compliance.toml"),
        Path("compliance.toml"),
        Path.cwd() / "config" / "compliance.toml",
    ]

    config_file = Path(toml_path) if toml_path else None
    if not config_file:
        for path in possible_paths:
            if path.exists():
                config_file = path
                break

    data: dict[str, dict[str, object]] = {}
    if config_file and config_file.exists():
        with open(config_file, "rb") as f:
            data = tomllib.load(f)

    privacy = data.get("privacy_logging", {})
    audit = data.get("audit_compliance", {})

    return ComplianceConfig(
        privacy_logging_enabled=bool(privacy.get("enabled", True)),
        pii_redaction_enabled=bool(privacy.get("redaction_enabled", True)),
        hash_session_ids=bool(privacy.get("hash_session_ids", True)),
        gdpr_compliance_required=bool(audit.get("gdpr_article_25", True)),
        audit_trail_required=True,
        soc2_compliance=bool(audit.get("soc2_cc6_1", True)),
        iso_27001_compliance=bool(audit.get("iso_27001_a12", True)),
        gdpr_article_25=bool(audit.get("gdpr_article_25", True)),
        gdpr_article_32=bool(audit.get("gdpr_article_32", True)),
    )
