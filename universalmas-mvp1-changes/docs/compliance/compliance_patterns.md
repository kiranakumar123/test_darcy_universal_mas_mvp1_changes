# Universal Framework Compliance Patterns

## Automatic Compliance (Recommended)

The framework automatically validates state updates when `state.copy()` is
invoked inside a `@streamlined_node` decorated function. The decorator sets a
ContextVar-based compliance context so all helper methods and direct `copy()`
usage transparently route through `FailClosedStateValidator`.

```python
@streamlined_node("my_agent", WorkflowPhase.GENERATION)
async def my_agent(state: UniversalWorkflowState) -> UniversalWorkflowState:
    # Automatic validation via ContextVar
    return state.copy(update={"workflow_phase": WorkflowPhase.REVIEW})
```

## Explicit Compliance (Edge Cases)

Use `update_state_with_compliance()` when updates occur outside normal node
execution or when manual control is required.

```python
from universal_framework.contracts.nodes import update_state_with_compliance

updated = update_state_with_compliance(
    state=current_state,
    updates={"workflow_phase": WorkflowPhase.GENERATION},
    source_agent="custom_agent",
    event="manual_update",
    validator=workflow._validator,
)
```

## Debugging Compliance

Diagnostic helpers aid debugging when validation fails or context is missing.

```python
from universal_framework.contracts.nodes import (
    is_compliance_active,
    validate_compliance_context,
)

if not is_compliance_active():
    print("Compliance is inactive")

info = validate_compliance_context()
print(info["message"])
```
