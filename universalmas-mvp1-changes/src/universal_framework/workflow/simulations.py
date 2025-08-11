"""Simulation functions for legacy agent behavior and new fallback paths."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from universal_framework.contracts.messages import AgentMessage
from universal_framework.contracts.state import EmailRequirements, EmailStrategy

# ============================================================================
# SIMULATION FUNCTIONS (LEGACY - DO NOT ALTER NAMES OR CONTRACTS)
# These functions are maintained for backward compatibility and testing.
# Real implementations should use the LangChain agents for production.
# ============================================================================


async def _simulate_requirement_collection(
    messages: list[AgentMessage],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Legacy simulation function - DO NOT ALTER."""
    await asyncio.sleep(0.1)
    user_input = ""
    for msg in messages:
        if msg.metadata.get("data", {}).get("user_input"):
            user_input = msg.metadata["data"]["user_input"]
            break
    missing_requirements = []
    requirements: dict[str, Any] = {}
    if user_input:
        if "audience" in user_input.lower():
            requirements["audience"] = "executives"
        else:
            missing_requirements.append("audience")
        if any(
            word in user_input.lower() for word in ["formal", "professional", "casual"]
        ):
            requirements["tone"] = "professional"
        else:
            missing_requirements.append("tone")
        if any(
            word in user_input.lower() for word in ["update", "announcement", "report"]
        ):
            requirements["purpose"] = "update"
        else:
            missing_requirements.append("purpose")
    else:
        missing_requirements = ["audience", "tone", "purpose", "key_points"]
    completion = max(0.0, (3 - len(missing_requirements)) / 3.0)
    return {
        "status": "complete" if completion >= 0.8 else "incomplete",
        "completion": completion,
        "requirements": requirements,
        "missing_requirements": missing_requirements,
        "confidence": 0.85 if completion >= 0.8 else 0.6,
    }


async def _simulate_strategy_generation(
    messages: list[AgentMessage],
    requirements: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Legacy simulation function - DO NOT ALTER."""
    await asyncio.sleep(0.15)
    if not requirements:
        return {
            "status": "failed",
            "completion": 0.0,
            "error": "No requirements provided",
        }
    strategy = {
        "approach": "data-driven narrative",
        "structure": ["executive summary", "key metrics", "next steps"],
        "tone_profile": requirements.get("tone", "professional"),
        "target_audience": requirements.get("audience", "general"),
        "primary_purpose": requirements.get("purpose", "communication"),
    }
    alternatives = [
        {"approach": "bullet-point summary", "emphasis": "brevity"},
        {"approach": "storytelling narrative", "emphasis": "engagement"},
    ]
    return {
        "status": "complete",
        "completion": 1.0,
        "strategy": strategy,
        "alternatives": alternatives,
        "confidence": 0.9,
    }


async def _simulate_confirmation_handling(
    messages: list[AgentMessage],
    strategy: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Legacy simulation function - DO NOT ALTER."""
    await asyncio.sleep(0.05)
    return {
        "status": "approved",
        "completion": 1.0,
        "approved": True,
        "approved_strategy": strategy,
        "feedback": "Strategy approved for implementation",
        "confirmation_timestamp": datetime.now().isoformat(),
    }


async def _simulate_email_generation(
    messages: list[AgentMessage],
    approved_strategy: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Legacy simulation function - DO NOT ALTER."""
    await asyncio.sleep(0.2)
    if not approved_strategy:
        return {
            "status": "failed",
            "completion": 0.0,
            "error": "No approved strategy provided",
        }
    email_content = {
        "subject": "Q4 Performance Update - Key Metrics and Next Steps",
        "body": """Dear Team,

I'm pleased to share our Q4 performance highlights
and outline our strategic priorities for the coming quarter.

**Key Metrics:**
- Revenue growth exceeded targets by 15%
- Customer satisfaction scores improved to 94%
- Market expansion goals achieved ahead of schedule

**Next Steps:**
1. Accelerate product development initiatives
2. Expand into three new geographic markets
3. Strengthen customer success programs

Thank you for your continued dedication and exceptional work.

Best regards,
[Your Name]""",
        "format": "html",
        "estimated_read_time": "2 minutes",
    }
    return {
        "status": "complete",
        "completion": 1.0,
        "email": email_content,
        "quality_score": 0.92,
        "metadata": {
            "word_count": 150,
            "tone_analysis": "professional and optimistic",
            "readability_score": 85,
            "generation_time": 2.3,
        },
    }


# ============================================================================
# NEW FALLBACK FUNCTIONS FOR STRATEGY GENERATOR NODE
# These functions provide simple fallback for new real agent implementations
# ============================================================================


def simulate_strategy_generation(requirements: EmailRequirements) -> EmailStrategy:
    """Generate a simple fallback strategy from requirements for StrategyGeneratorNode."""
    audience = ", ".join(requirements.audience)
    return EmailStrategy(
        overall_approach=f"Fallback strategy for {requirements.purpose}",
        tone_strategy=requirements.tone,
        structure_strategy=requirements.key_messages,
        messaging_strategy={},
        personalization_strategy={},
        estimated_impact="medium",
        confidence_score=0.5,
        target_audience=audience,
        tone=requirements.tone,
        approach=f"Fallback strategy for {requirements.purpose}",
        key_messages=requirements.key_messages,
        timing_considerations="Standard timing",
        success_metrics="Standard email engagement metrics",
    )
