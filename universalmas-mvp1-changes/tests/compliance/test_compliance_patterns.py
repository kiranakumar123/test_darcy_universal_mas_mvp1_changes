import asyncio

import pytest

from universal_framework.contracts.nodes import (
    is_compliance_active,
    streamlined_node,
    update_state_with_compliance,
    validate_compliance_context,
)
from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.workflow.builder import create_streamlined_workflow


@pytest.mark.asyncio
async def test_automatic_compliance_through_contextvar() -> None:
    workflow = create_streamlined_workflow(
        use_real_agents=False, enable_compliance=True
    )
    state = UniversalWorkflowState(session_id="s", user_id="u", auth_token="t" * 10)
    result = await workflow.ainvoke(state)
    assert result.audit_trail


def test_explicit_compliance_helper() -> None:
    workflow = create_streamlined_workflow(
        use_real_agents=False, enable_compliance=True
    )
    validator = workflow._validator
    state = UniversalWorkflowState(session_id="s", user_id="u", auth_token="t" * 10)
    updated = update_state_with_compliance(
        state,
        updates={"workflow_phase": WorkflowPhase.BATCH_DISCOVERY},
        source_agent="email_workflow_orchestrator",
        event="manual",
        validator=validator,
    )
    assert updated.workflow_phase == WorkflowPhase.BATCH_DISCOVERY
    assert len(updated.audit_trail) == 1


@pytest.mark.asyncio
async def test_compliance_diagnostics() -> None:
    diagnostics = validate_compliance_context()
    assert diagnostics["status"] == "inactive"

    workflow = create_streamlined_workflow(
        use_real_agents=False, enable_compliance=True
    )
    validator = workflow._validator

    @streamlined_node("email_workflow_orchestrator", WorkflowPhase.INITIALIZATION)
    async def diag_node(state: UniversalWorkflowState) -> UniversalWorkflowState:
        assert is_compliance_active()
        info = validate_compliance_context()
        assert info["status"] == "active"
        return state

    diag_node._validator = validator
    await diag_node(
        UniversalWorkflowState(session_id="s", user_id="u", auth_token="t" * 10)
    )


@pytest.mark.asyncio
async def test_contextvar_isolation() -> None:
    async def run_node(node_name: str, validator):
        @streamlined_node(node_name, WorkflowPhase.INITIALIZATION)
        async def simple(state: UniversalWorkflowState) -> UniversalWorkflowState:
            ctx = validate_compliance_context()
            assert ctx["status"] == "active"
            assert ctx["has_validator"]
            assert ctx["has_source_agent"]
            return state

        simple._validator = validator
        await simple(
            UniversalWorkflowState(session_id="s", user_id="u", auth_token="t" * 10)
        )

    wf1 = create_streamlined_workflow(use_real_agents=False, enable_compliance=True)
    wf2 = create_streamlined_workflow(use_real_agents=False, enable_compliance=True)
    await asyncio.gather(
        run_node("batch_requirements_collector", wf1._validator),
        run_node("batch_requirements_collector", wf2._validator),
    )
