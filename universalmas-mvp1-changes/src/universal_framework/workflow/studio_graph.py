"""
LangGraph Studio Workflow
========================
Workflow graph for LangGraph Studio visualization using main framework patterns.
This follows the Universal Multi-Agent System Framework architecture.
"""

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

# Import the proper UniversalWorkflowState from the main framework
from universal_framework.contracts.state import UniversalWorkflowState


def initialization_node(state: UniversalWorkflowState) -> UniversalWorkflowState:
    """Initialize the workflow with session setup."""
    print(f"🚀 Initialization Phase - Session: {state.session_id}")

    return state.copy(
        update={
            "context_data": {
                **state.context_data,
                "current_phase": "initialization",
                "initialized_at": "2025-07-23",
                "framework": "Universal Multi-Agent System",
            },
            "messages": [
                *state.messages,
                AIMessage(
                    content="🚀 Universal Framework initialized. Ready for discovery phase."
                ),
            ],
        }
    )


def discovery_node(state: UniversalWorkflowState) -> UniversalWorkflowState:
    """Discovery phase: Gather requirements and analyze context."""
    print("🔍 Discovery Phase - Processing requirements")

    # Simulate requirement gathering
    requirements = {
        "user_objectives": "Multi-agent workflow visualization",
        "stakeholders": ["Developer", "System Architect"],
        "constraints": ["Enterprise compliance", "Audit requirements"],
        "scope": "LangGraph Studio integration",
    }

    return state.copy(
        update={
            "context_data": {
                **state.context_data,
                "current_phase": "discovery",
                "requirements": requirements,
            },
            "messages": [
                *state.messages,
                AIMessage(
                    content="🔍 Discovery complete. Requirements gathered and analyzed."
                ),
            ],
        }
    )


def analysis_node(state: UniversalWorkflowState) -> UniversalWorkflowState:
    """Analysis phase: Evaluate options and assess feasibility."""
    print("📊 Analysis Phase - Evaluating options")

    analysis = {
        "workflow_complexity": "High",
        "integration_feasibility": "Excellent",
        "risk_assessment": "Low",
        "recommended_approach": "LangGraph Studio with Docker backend",
        "estimated_effort": "2-3 days",
    }

    return state.copy(
        update={
            "context_data": {
                **state.context_data,
                "current_phase": "analysis",
                "analysis": analysis,
            },
            "messages": [
                *state.messages,
                AIMessage(content="📊 Analysis complete. Workflow approach validated."),
            ],
        }
    )


def generation_node(state: UniversalWorkflowState) -> UniversalWorkflowState:
    """Generation phase: Create deliverables and solutions."""
    print("🎨 Generation Phase - Creating deliverables")

    deliverables = {
        "workflow_graph": "Universal 6-phase workflow",
        "studio_integration": "LangGraph Studio configuration",
        "documentation": "Setup guides and API documentation",
        "visualization": "Interactive workflow diagrams",
    }

    return state.copy(
        update={
            "context_data": {
                **state.context_data,
                "current_phase": "generation",
                "deliverables": deliverables,
            },
            "messages": [
                *state.messages,
                AIMessage(content="🎨 Generation complete. All deliverables created."),
            ],
        }
    )


def review_node(state: UniversalWorkflowState) -> UniversalWorkflowState:
    """Review phase: Quality validation and compliance check."""
    print("✅ Review Phase - Validating quality")

    return state.copy(
        update={
            "context_data": {
                **state.context_data,
                "current_phase": "review",
                "quality_score": 95,
                "compliance_status": "Passed",
                "review_notes": "Excellent integration with enterprise standards",
            },
            "messages": [
                *state.messages,
                AIMessage(
                    content="✅ Review complete. Quality validated and approved."
                ),
            ],
        }
    )


def delivery_node(state: UniversalWorkflowState) -> UniversalWorkflowState:
    """Delivery phase: Package and distribute results."""
    print("📦 Delivery Phase - Packaging results")

    return state.copy(
        update={
            "context_data": {
                **state.context_data,
                "current_phase": "delivery",
                "delivery_status": "Completed",
                "package_format": "LangGraph Studio Project",
                "deployment_ready": True,
            },
            "messages": [
                *state.messages,
                AIMessage(
                    content="📦 Delivery complete. Universal Framework ready for use!"
                ),
            ],
        }
    )


def create_workflow_graph() -> StateGraph:
    """
    Create the Universal Multi-Agent System workflow graph for LangGraph Studio.

    This creates a visual representation of our 6-phase workflow:
    1. Initialization → 2. Discovery → 3. Analysis → 4. Generation → 5. Review → 6. Delivery

    Returns:
        StateGraph: Compiled workflow graph ready for Studio visualization
    """

    # Create the state graph
    workflow = StateGraph(UniversalWorkflowState)

    # Add all workflow nodes
    workflow.add_node("initialization", initialization_node)
    workflow.add_node("discovery", discovery_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("generation", generation_node)
    workflow.add_node("review", review_node)
    workflow.add_node("delivery", delivery_node)

    # Define the workflow flow: Linear progression through phases
    workflow.add_edge(START, "initialization")
    workflow.add_edge("initialization", "discovery")
    workflow.add_edge("discovery", "analysis")
    workflow.add_edge("analysis", "generation")
    workflow.add_edge("generation", "review")
    workflow.add_edge("review", "delivery")
    workflow.add_edge("delivery", END)

    # Compile the graph
    compiled_graph = workflow.compile()

    print("🎯 Universal Multi-Agent System Workflow Graph created!")
    print(
        "📊 Phases: Initialization → Discovery → Analysis → Generation → Review → Delivery"
    )

    return compiled_graph


# Test function for development
def test_workflow():
    """Test the workflow with sample input."""
    graph = create_workflow_graph()

    # Create proper UniversalWorkflowState instance
    initial_state = UniversalWorkflowState(
        session_id="test-session-123",
        user_id="test-user",
        auth_token="test-token-123",
        messages=[HumanMessage(content="Initialize Universal Framework workflow")],
        context_data={
            "current_phase": "start",
            "requirements": {},
            "analysis": {},
            "deliverables": {},
        },
    )

    print("🧪 Testing workflow execution...")
    result = graph.invoke(initial_state)

    # Handle the fact that LangGraph returns a dict representation
    if isinstance(result, dict):
        current_phase = result.get("context_data", {}).get("current_phase", "unknown")
    else:
        current_phase = result.context_data.get("current_phase", "unknown")

    print(f"✅ Workflow completed! Final phase: {current_phase}")
    return result


if __name__ == "__main__":
    # Create and test the workflow
    test_workflow()
