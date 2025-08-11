"""Feature flags system for safe mode operation and enterprise feature management."""

from __future__ import annotations

import os
from typing import Any


class SafeModeFeatureFlags:
    """
    Feature flags system with safe defaults.

    By default, operates in safe mode with enterprise features disabled
    until explicitly enabled via environment variables.
    """

    def __init__(self) -> None:
        """Initialize feature flags with safe defaults."""
        # Core features (always enabled)
        self.core_features = {
            "WORKFLOW_EXECUTION": True,
            "SESSION_MANAGEMENT": True,
            "HEALTH_ENDPOINTS": True,
            "BASIC_LOGGING": True,
        }

        # Enterprise features (disabled by default for safety)
        # Use direct environment variable checking to avoid circular dependency
        self.enterprise_features = {
            "ENTERPRISE_FEATURES": self._env_to_bool("ENTERPRISE_FEATURES", False),
            "ENTERPRISE_AUTH_MIDDLEWARE": self._env_to_bool(
                "ENTERPRISE_AUTH_MIDDLEWARE", False
            ),
            "ENTERPRISE_AUDIT_VALIDATION": self._env_to_bool(
                "ENTERPRISE_AUDIT_VALIDATION", False
            ),
            "LANGSMITH_TRACING": self._env_to_bool("LANGSMITH_TRACING", False),
            "PII_REDACTION": self._env_to_bool("PII_REDACTION", False),
            "AUTHORIZATION_MATRIX": self._env_to_bool("AUTHORIZATION_MATRIX", False),
            "COMPLIANCE_MONITORING": self._env_to_bool("COMPLIANCE_MONITORING", False),
        }

    def _env_to_bool(self, key: str, default: bool) -> bool:
        """Convert environment variable to boolean with safe mode override logic."""
        # In safe mode, force enterprise features to False regardless of environment
        if self._is_safe_mode_explicitly_enabled() and key.startswith(
            ("ENTERPRISE_", "LANGSMITH_", "PII_", "AUTHORIZATION_", "COMPLIANCE_")
        ):
            return False

        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def _is_safe_mode_explicitly_enabled(self) -> bool:
        """Check if safe mode is explicitly enabled via environment variable."""
        return os.getenv("SAFE_MODE", "true").lower() in ("true", "1", "yes", "on")

    def is_safe_mode(self) -> bool:
        """
        Check if running in safe mode.

        Safe mode is active when:
        1. SAFE_MODE environment variable is true (default)
        2. ENTERPRISE_FEATURES is not explicitly enabled
        """
        safe_mode_env = self._is_safe_mode_explicitly_enabled()
        enterprise_disabled = not self.enterprise_features.get(
            "ENTERPRISE_FEATURES", False
        )

        return safe_mode_env or enterprise_disabled

    def is_enabled(self, feature: str) -> bool:
        """Check if a specific feature is enabled."""
        # Check core features first
        if feature in self.core_features:
            return self.core_features[feature]

        # Check enterprise features
        if feature in self.enterprise_features:
            return self.enterprise_features[feature]

        # Unknown features are disabled by default
        return False

    def get_feature_status(self) -> dict[str, Any]:
        """Get complete feature status for debugging and monitoring."""
        return {
            "safe_mode": self.is_safe_mode(),
            "core_features": self.core_features,
            "enterprise_features": self.enterprise_features,
            "environment_variables": {
                "SAFE_MODE": os.getenv("SAFE_MODE", "true"),
                "ENTERPRISE_FEATURES": os.getenv("ENTERPRISE_FEATURES", "false"),
                "ENTERPRISE_AUTH_MIDDLEWARE": os.getenv(
                    "ENTERPRISE_AUTH_MIDDLEWARE", "false"
                ),
                "ENTERPRISE_AUDIT_VALIDATION": os.getenv(
                    "ENTERPRISE_AUDIT_VALIDATION", "false"
                ),
                "LANGSMITH_TRACING": os.getenv("LANGSMITH_TRACING", "false"),
                "PII_REDACTION": os.getenv("PII_REDACTION", "false"),
                "AUTHORIZATION_MATRIX": os.getenv("AUTHORIZATION_MATRIX", "false"),
                "COMPLIANCE_MONITORING": os.getenv("COMPLIANCE_MONITORING", "false"),
            },
        }

    def get_enabled_features(self) -> list[str]:
        """Get list of currently enabled features."""
        enabled = []

        # Add enabled core features
        for feature, enabled_status in self.core_features.items():
            if enabled_status:
                enabled.append(feature)

        # Add enabled enterprise features
        for feature, enabled_status in self.enterprise_features.items():
            if enabled_status:
                enabled.append(feature)

        return enabled

    def get_disabled_features(self) -> list[str]:
        """Get list of currently disabled features."""
        disabled = []

        # Add disabled core features (should be rare)
        for feature, enabled_status in self.core_features.items():
            if not enabled_status:
                disabled.append(feature)

        # Add disabled enterprise features
        for feature, enabled_status in self.enterprise_features.items():
            if not enabled_status:
                disabled.append(feature)

        return disabled


# Global feature flags instance
feature_flags = SafeModeFeatureFlags()


def is_safe_mode() -> bool:
    """Convenience function to check if safe mode is active."""
    return feature_flags.is_safe_mode()


def is_feature_enabled(feature: str) -> bool:
    """Convenience function to check if a feature is enabled."""
    return feature_flags.is_enabled(feature)


def get_safe_mode_status() -> dict[str, Any]:
    """Get safe mode status for debugging and monitoring."""
    flags_status = feature_flags.get_feature_status()

    return {
        "safe_mode": "ACTIVE" if flags_status["safe_mode"] else "DISABLED",
        "timestamp": "2025-07-21T00:00:00Z",  # Would use datetime.now().isoformat() in real implementation
        "enabled_features": feature_flags.get_enabled_features(),
        "disabled_features": feature_flags.get_disabled_features(),
        "note": "Safe mode provides graceful degradation when enterprise features are incomplete",
        "configuration": flags_status["environment_variables"],
    }
