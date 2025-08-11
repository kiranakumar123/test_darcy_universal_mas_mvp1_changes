from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback
    import tomli as tomllib  # type: ignore


def load_compliance_config() -> dict[str, Any]:
    """Load enterprise compliance configuration with environment overrides."""

    # Import feature flags to check safe mode
    from .feature_flags import feature_flags

    # In safe mode, return disabled compliance configuration
    if feature_flags.is_safe_mode():
        return {
            "enterprise_compliance": {"enabled": False},
            "redaction_config": {},
            "audit_settings": {},
        }

    config_path = Path("config/compliance.toml")
    if not config_path.exists():
        # Only enable by default if not in safe mode and compliance monitoring is enabled
        enabled = feature_flags.is_enabled("COMPLIANCE_MONITORING")
        return {
            "enterprise_compliance": {"enabled": enabled},
            "redaction_config": {},
            "audit_settings": {},
        }

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    config.setdefault("audit_settings", {})
    config["audit_settings"]["hash_salt"] = os.environ.get(
        "COMPLIANCE_HASH_SALT",
        config["audit_settings"].get("hash_salt", "default_enterprise_salt"),
    )

    # Only allow environment override if not in safe mode
    if (
        not feature_flags.is_safe_mode()
        and "ENTERPRISE_COMPLIANCE_ENABLED" in os.environ
    ):
        config["enterprise_compliance"]["enabled"] = (
            os.environ["ENTERPRISE_COMPLIANCE_ENABLED"].lower() == "true"
        )
    elif feature_flags.is_safe_mode():
        # Force disable in safe mode regardless of config
        config["enterprise_compliance"]["enabled"] = False

    return config
