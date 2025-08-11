"""
Universal Framework Nodes - LangGraph-Aligned Architecture

Node implementations organized by responsibility:
- agents/: LLM-powered agent nodes for AI capabilities

Each node maintains single responsibility and is orchestrated via LangGraph conditional edges.
"""

# Re-export key components from submodules
from . import agents
from .base import BaseNode

__all__ = [
    "agents",
    "BaseNode",
]

# Node registry for dynamic loading (maintained for backward compatibility)
NODE_REGISTRY: dict[str, type] = {}


def register_node(name: str, node_class: type) -> None:
    """Register a node class for dynamic loading."""
    NODE_REGISTRY[name] = node_class


def get_node(name: str) -> type | None:
    """Get a registered node class."""
    return NODE_REGISTRY.get(name)


def list_nodes() -> list[str]:
    """List all registered nodes."""
    return list(NODE_REGISTRY.keys())
