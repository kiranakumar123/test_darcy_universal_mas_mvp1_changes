"""
LangGraph Studio Workflow Entry Point
====================================
This module provides the graph creation function for LangGraph Studio.
"""

from typing import Any

from langgraph.graph import StateGraph

from universal_framework.workflow.builder import WorkflowBuilder


def create_workflow_graph() -> StateGraph:
    """
    Create the workflow graph for LangGraph Studio.

    This function is referenced in langgraph.json and provides
    the entry point for Studio visualization and debugging.

    Returns:
        StateGraph: Compiled workflow graph
    """
    # Use our existing workflow builder
    builder = WorkflowBuilder()

    # Build the workflow with in-memory checkpointing
    workflow = builder.build_workflow(
        checkpointer=None,  # No Redis - use in-memory
        recursion_limit=200,  # Further increased limit for production robustness
    )

    return workflow


def create_workflow_with_config(config: dict[str, Any] = None) -> StateGraph:
    """
    Create workflow with custom configuration for Studio.

    Args:
        config: Optional configuration dictionary

    Returns:
        StateGraph: Configured workflow graph
    """
    if config is None:
        config = {}

    builder = WorkflowBuilder()

    # Apply any custom configuration
    recursion_limit = config.get(
        "recursion_limit", 200
    )  # Further increased default limit

    workflow = builder.build_workflow(
        checkpointer=None, recursion_limit=recursion_limit
    )

    return workflow
