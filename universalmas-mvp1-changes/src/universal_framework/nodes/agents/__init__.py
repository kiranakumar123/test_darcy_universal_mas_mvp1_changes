"""
LangGraph-Aligned Agent Nodes

LLM-powered agents that implement specific business capabilities.
Each agent has single responsibility and is orchestrated via LangGraph conditional edges.

Architecture:
- Single responsibility per agent
- Async-first with enterprise observability
- Defensive programming for LangGraph state handling
- Modern Python 3.11+ patterns (match/case, | union types)
"""

from .email_generation_agent import EmailGenerationAgent
from .intent_analysis_agent import IntentAnalysisAgent, classify_user_intent_async
from .intent_classifier_agent import IntentClassifierAgent, UserIntent
from .requirements_collection_agent import RequirementsCollectionAgent
from .strategy_generation_agent import StrategyGenerationAgent

__all__ = [
    "EmailGenerationAgent",
    "IntentAnalysisAgent",
    "IntentClassifierAgent",
    "RequirementsCollectionAgent",
    "StrategyGenerationAgent",
    "UserIntent",
    "classify_user_intent_async",
]
