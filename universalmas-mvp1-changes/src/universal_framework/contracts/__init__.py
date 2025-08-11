"""Universal Framework Contracts

Type definitions, schemas, and interfaces for the Universal Framework.
"""

from .exceptions import (
    LLMConnectionError,
    PerformanceTimeoutError,
    StrategyValidationError,
    UniversalFrameworkError,
)
from .messages import AgentMessage, create_agent_message, extract_agent_messages
from .nodes import NodeContract
from .state import (
    BatchCollectionResponse,
    ConflictAnalysis,
    EmailDeliveryResponse,
    EmailRequirements,
    EmailStrategy,
    GeneratedEmail,
    GenerationProgressResponse,
    StrategyPresentationResponse,
    UniversalWorkflowState,
    ValidationResult,
    WorkflowPhase,
)

__all__ = [
    "UniversalWorkflowState",
    "WorkflowPhase",
    "EmailRequirements",
    "EmailStrategy",
    "ConflictAnalysis",
    "GeneratedEmail",
    "ValidationResult",
    "BatchCollectionResponse",
    "StrategyPresentationResponse",
    "GenerationProgressResponse",
    "EmailDeliveryResponse",
    "NodeContract",
    "AgentMessage",
    "create_agent_message",
    "extract_agent_messages",
    "UniversalFrameworkError",
    "LLMConnectionError",
    "StrategyValidationError",
    "PerformanceTimeoutError",
]
