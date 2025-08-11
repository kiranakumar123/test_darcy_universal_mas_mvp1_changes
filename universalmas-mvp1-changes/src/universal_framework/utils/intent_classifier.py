"""
Intent Classification for Universal Multi-Agent System
====================================================
This module provides intent classification to route users to appropriate workflows
or provide general assistance before entering specific task workflows.
"""

import json
import re
from enum import Enum
from pathlib import Path


class UserIntent(Enum):
    """User intent classifications for workflow routing."""

    # General intents
    HELP_REQUEST = "help_request"
    CAPABILITIES_INQUIRY = "capabilities_inquiry"
    GREETING = "greeting"

    # Task-specific intents
    OCM_COMMUNICATION = "ocm_communication"
    DOCUMENT_GENERATION = "document_generation"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    PROCESS_OPTIMIZATION = "process_optimization"

    # Meta intents
    UNCLEAR = "unclear"
    INVALID = "invalid"


class IntentClassifier:
    """Classifies user input to determine appropriate workflow routing."""

    def __init__(self):
        """Initialize intent classification patterns."""
        # Load patterns from capabilities guidance file for consistency

    def __init__(self):
        """Initialize intent classification patterns."""
        # Load patterns from capabilities guidance file for consistency
        self.capabilities_config = self._load_capabilities_guidance_config()

        # Build patterns from config + hardcoded fallbacks
        self.intent_patterns = {
            UserIntent.HELP_REQUEST: self._build_help_patterns(),
            UserIntent.CAPABILITIES_INQUIRY: [
                r"\bwhat are your capabilities\b",
                r"\bwhat can you help with\b",
                r"\bwhat services\b",
                r"\bwhat features\b",
                r"\bwhat tools\b",
                r"\bwhat can you do\b",
                r"\blist capabilities\b",
            ],
            UserIntent.GREETING: [
                r"\b(hello|hi|hey|greetings)\b",
                r"\bgood (morning|afternoon|evening)\b",
            ],
            UserIntent.OCM_COMMUNICATION: [
                r"\b(change|organizational|communication|stakeholder)\b",
                r"\bchange management\b",
                r"\bstakeholder.*communication\b",
                r"\borganizational.*change\b",
            ],
            UserIntent.DOCUMENT_GENERATION: [
                r"\b(document|report|proposal|presentation)\b",
                r"\bcreate.*document\b",
                r"\bgenerate.*report\b",
                r"\bwrite.*proposal\b",
                r"\bdraft.*document\b",
            ],
            UserIntent.DATA_ANALYSIS: [
                r"\b(analyze|analysis|data|metrics|insights)\b",
                r"\bexamine.*data\b",
                r"\banalyze.*metrics\b",
                r"\bdata.*insights\b",
            ],
            UserIntent.CONTENT_CREATION: [
                r"\b(content|blog|article|social|marketing)\b",
                r"\bcreate.*content\b",
                r"\bwrite.*blog\b",
                r"\bmarketing.*content\b",
            ],
            UserIntent.PROCESS_OPTIMIZATION: [
                r"\b(process|workflow|optimization|efficiency)\b",
                r"\boptimize.*process\b",
                r"\bimprove.*workflow\b",
                r"\bprocess.*design\b",
            ],
        }

        # Combine help and capabilities patterns for broader detection
        self.general_help_patterns = (
            self.intent_patterns[UserIntent.HELP_REQUEST]
            + self.intent_patterns[UserIntent.CAPABILITIES_INQUIRY]
            + self.intent_patterns[UserIntent.GREETING]
        )

    def _load_capabilities_guidance_config(self) -> dict:
        """Load capabilities guidance configuration for consistent help detection."""
        try:
            config_path = Path(
                "src/universal_framework/interpreter/capabilities_guidance.json"
            )
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # Fallback patterns if file not found
            return {
                "input_recognition": {
                    "example_phrases": ["help", "what can I do", "I'm confused"],
                    "regex_patterns": ["(?i)(help|confused|stuck|lost)"],
                }
            }

    def _build_help_patterns(self) -> list[str]:
        """Build help detection patterns from capabilities guidance file."""
        patterns = []

        # Add regex patterns from config
        config_patterns = self.capabilities_config.get("input_recognition", {}).get(
            "regex_patterns", []
        )
        patterns.extend(config_patterns)

        # Add example phrases converted to regex patterns
        example_phrases = self.capabilities_config.get("input_recognition", {}).get(
            "example_phrases", []
        )
        for phrase in example_phrases:
            # Convert phrase to regex pattern (escape special chars, make case insensitive)
            escaped_phrase = re.escape(phrase.lower())
            patterns.append(f"(?i)\\b{escaped_phrase}\\b")

        # Add fallback patterns
        fallback_patterns = [
            r"\b(help|assist|support|guide)\b",
            r"\bwhat can you\b",
            r"\bhow can you\b",
            r"\bwhat do you do\b",
            r"\bcan you help\b",
            r"\bi need help\b",
            r"\bshow me\b",
        ]
        patterns.extend(fallback_patterns)

        return patterns

    def _setup_patterns(self) -> None:
        """Initialize intent patterns after enum initialization."""
        # Combine help and capabilities patterns for broader detection
        help_patterns = [
            r"\bhelp\b",
            r"\bassist\b",
            r"\bsupport\b",
            r"\bguide\b",
            r"\bhow.*help\b",
        ]
        capabilities_patterns = [
            r"\bwhat.*can.*do\b",
            r"\bcapabilit(y|ies)\b",
            r"\bfeatures\b",
            r"\bfunctions\b",
            r"\bwhat do you offer\b",
            r"\blist.*capabilities\b",
            r"\bwhat features\b",
        ]

        self.general_help_patterns = help_patterns + capabilities_patterns

    def classify_intent(self, user_input: str) -> UserIntent:
        """
        Classify user input into appropriate intent category.

        Args:
            user_input: Raw user input text

        Returns:
            UserIntent: Classified intent for routing
        """
        if not user_input or not user_input.strip():
            return UserIntent.INVALID

        user_lower = user_input.lower().strip()

        # Check for general help patterns first (highest priority)
        for pattern in self.general_help_patterns:
            if re.search(pattern, user_lower, re.IGNORECASE):
                return UserIntent.HELP_REQUEST

        # Check specific task intents
        for intent, patterns in self.intent_patterns.items():
            if intent in [
                UserIntent.HELP_REQUEST,
                UserIntent.CAPABILITIES_INQUIRY,
                UserIntent.GREETING,
            ]:
                continue  # Already checked above

            for pattern in patterns:
                if re.search(pattern, user_lower, re.IGNORECASE):
                    return intent

        # If no specific patterns match, check if it's a reasonable request
        if len(user_lower.split()) >= 3:  # Substantial input
            return UserIntent.UNCLEAR
        else:
            return UserIntent.INVALID

    def should_show_capabilities(self, intent: UserIntent) -> bool:
        """Determine if capabilities guidance should be shown for this intent."""
        return intent in [
            UserIntent.HELP_REQUEST,
            UserIntent.CAPABILITIES_INQUIRY,
            UserIntent.GREETING,
            UserIntent.UNCLEAR,
        ]

    def get_workflow_type(self, intent: UserIntent) -> str | None:
        """Map intent to appropriate workflow type."""
        workflow_mapping = {
            UserIntent.OCM_COMMUNICATION: "ocm_communications",
            UserIntent.DOCUMENT_GENERATION: "document_generation",
            UserIntent.DATA_ANALYSIS: "data_analysis",
            UserIntent.CONTENT_CREATION: "content_creation",
            UserIntent.PROCESS_OPTIMIZATION: "process_optimization",
        }
        return workflow_mapping.get(intent)


# Global classifier instance
intent_classifier = IntentClassifier()


def classify_user_intent(user_input: str) -> UserIntent:
    """
    Classify user intent for workflow routing.

    Args:
        user_input: Raw user input text

    Returns:
        UserIntent: Classified intent
    """
    return intent_classifier.classify_intent(user_input)


def should_show_capabilities_response(user_input: str) -> bool:
    """
    Determine if user input warrants showing capabilities guidance.

    Args:
        user_input: Raw user input text

    Returns:
        bool: True if capabilities should be shown
    """
    intent = classify_user_intent(user_input)
    return intent_classifier.should_show_capabilities(intent)
