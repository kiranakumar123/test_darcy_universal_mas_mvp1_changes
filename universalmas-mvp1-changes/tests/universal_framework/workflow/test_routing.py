import pytest

from universal_framework.contracts.state import UniversalWorkflowState
from universal_framework.workflow.routing import EnhancedWorkflowRouter, RoutingDecision


@pytest.mark.asyncio
async def test_enhanced_router_basic_routing() -> None:
    router = EnhancedWorkflowRouter()
    state = UniversalWorkflowState(session_id="test", user_id="u", auth_token="t" * 10)
    result = router.route_from_node("email_workflow_orchestrator", state)
    assert isinstance(result.next_node, str)
    assert result.decision_type in RoutingDecision
