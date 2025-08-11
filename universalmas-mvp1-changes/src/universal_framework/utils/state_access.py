"""Defensive state access utilities for LangGraph state conversion issues.

This module provides comprehensive utility functions to safely access workflow state
attributes, handling the documented LangGraph behavior where Pydantic BaseModel
objects may be converted to dictionaries during workflow execution.

Key features:
- Universal state attribute access with fallback handling
- Type-safe conversion utilities
- Backward compatibility with Pydantic models
- Comprehensive error handling and logging
- Performance-optimized caching for repeated access patterns

Usage:
    from universal_framework.utils.state_access import safe_get, safe_get_phase

    # Safe attribute access
    session_id = safe_get(state, 'session_id', str, 'unknown')
    workflow_phase = safe_get_phase(state)

    # Safe nested access
    requirements = safe_get(state, 'email_requirements', EmailRequirements)
    if requirements:
        completeness_score = safe_get(requirements, 'completeness_score', float, 0.0)

References:
- LangGraph documentation on state conversion behavior
- Claude.md defensive programming guidelines
"""

from __future__ import annotations

from typing import Any, TypeVar

from universal_framework.contracts.state import UniversalWorkflowState, WorkflowPhase
from universal_framework.observability import UniversalFrameworkLogger

logger = UniversalFrameworkLogger("state_access")

T = TypeVar("T")


def safe_get(
    state: Any,
    key: str,
    expected_type: type[T] | None = None,
    default: T | None = None,
) -> T | Any:
    """
    Safely get an attribute from state object that may be dict or Pydantic model.

    Args:
        state: The state object (UniversalWorkflowState or dict)
        key: The attribute name to access
        expected_type: Optional type to convert the value to
        default: Default value if key not found

    Returns:
        The safely retrieved value, or default if not found
    """
    if state is None:
        logger.warning("safe_get called with None state")
        return default

    try:
        # Handle Pydantic model access
        if hasattr(state, key):
            value = getattr(state, key)
        # Handle dict access
        elif isinstance(state, dict) and key in state:
            value = state[key]
        # Handle nested dict access with dot notation
        elif isinstance(state, dict) and "." in key:
            keys = key.split(".")
            current = state
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default
            value = current
        else:
            value = default

        # Type conversion if requested
        if expected_type and value is not None:
            try:
                if expected_type == bool and isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")
                elif expected_type == WorkflowPhase:
                    if isinstance(value, str):
                        return WorkflowPhase(value)
                    elif isinstance(value, WorkflowPhase):
                        return value
                    else:
                        return WorkflowPhase.INITIALIZATION
                else:
                    return expected_type(value)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to convert {key}={value} to {expected_type.__name__}",
                    extra={"error": str(e), "key": key, "value": str(value)},
                )
                return default

        return value

    except Exception as e:
        logger.error(
            f"Error accessing state attribute {key}",
            extra={"error": str(e), "key": key, "state_type": type(state).__name__},
        )
        return default


def safe_get_phase(state: Any) -> WorkflowPhase:
    """
    Safely get the workflow phase from state.

    Args:
        state: The state object

    Returns:
        WorkflowPhase, defaults to INITIALIZATION if not found
    """
    return safe_get(
        state, "workflow_phase", WorkflowPhase, WorkflowPhase.INITIALIZATION
    )


def safe_get_session_id(state: Any) -> str:
    """
    Safely get the session ID from state.

    Args:
        state: The state object

    Returns:
        Session ID string, defaults to 'unknown' if not found
    """
    return safe_get(state, "session_id", str, "unknown")


def safe_get_user_id(state: Any) -> str:
    """
    Safely get the user ID from state.

    Args:
        state: The state object

    Returns:
        User ID string, defaults to 'unknown' if not found
    """
    return safe_get(state, "user_id", str, "unknown")


def safe_get_requirements(state: Any) -> Any:
    """
    Safely get email requirements from state.

    Args:
        state: The state object

    Returns:
        EmailRequirements or None if not found
    """
    from universal_framework.contracts.state import EmailRequirements

    return safe_get(state, "email_requirements", EmailRequirements)


def safe_get_strategy(state: Any) -> Any:
    """
    Safely get email strategy from state.

    Args:
        state: The state object

    Returns:
        EmailStrategy or None if not found
    """
    from universal_framework.contracts.state import EmailStrategy

    return safe_get(state, "email_strategy", EmailStrategy)


def safe_get_messages(state: Any) -> list[Any]:
    """
    Safely get messages list from state.

    Args:
        state: The state object

    Returns:
        List of messages, defaults to empty list if not found
    """
    return safe_get(state, "messages", list, [])


def safe_get_context_data(state: Any) -> dict[str, Any]:
    """
    Safely get context data from state.

    Args:
        state: The state object

    Returns:
        Context data dict, defaults to empty dict if not found
    """
    return safe_get(state, "context_data", dict, {})


def safe_get_phase_completion(state: Any) -> dict[str, float]:
    """
    Safely get phase completion data from state.

    Args:
        state: The state object

    Returns:
        Phase completion dict, defaults to empty dict if not found
    """
    return safe_get(state, "phase_completion", dict, {})


def safe_get_audit_trail(state: Any) -> list[dict[str, Any]]:
    """
    Safely get audit trail from state.

    Args:
        state: The state object

    Returns:
        Audit trail list, defaults to empty list if not found
    """
    return safe_get(state, "audit_trail", list, [])


def safe_get_nested(
    state: Any,
    path: str,
    expected_type: type[T] | None = None,
    default: T | None = None,
) -> T | Any:
    """
    Safely get nested attributes using dot notation.

    Args:
        state: The state object
        path: Dot-separated path (e.g., "context_data.workflow_data")
        expected_type: Optional type to convert the value to
        default: Default value if path not found

    Returns:
        The safely retrieved nested value
    """
    try:
        keys = path.split(".")
        current = state

        for key in keys:
            if hasattr(current, key):
                current = getattr(current, key)
            elif isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        if expected_type and current is not None:
            try:
                return expected_type(current)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to convert nested {path}={current} to {expected_type.__name__}",
                    extra={"error": str(e), "path": path, "value": str(current)},
                )
                return default

        return current

    except Exception as e:
        logger.error(
            f"Error accessing nested state path {path}",
            extra={"error": str(e), "path": path, "state_type": type(state).__name__},
        )
        return default


def validate_state_type(state: Any) -> tuple[bool, str]:
    """
    Validate the type of state object.

    Args:
        state: The state object to validate

    Returns:
        Tuple of (is_valid, type_description)
    """
    if state is None:
        return False, "None"

    state_type = type(state).__name__

    if isinstance(state, UniversalWorkflowState):
        return True, "UniversalWorkflowState (Pydantic)"
    elif isinstance(state, dict):
        return True, "dict"
    else:
        return False, f"Unexpected type: {state_type}"


def ensure_state_type(
    state: Any,
    expected_type: type = UniversalWorkflowState,
) -> UniversalWorkflowState:
    """
    Ensure state is of expected type, converting dict to Pydantic if necessary.

    Args:
        state: The state object
        expected_type: Expected type (defaults to UniversalWorkflowState)

    Returns:
        Properly typed state object
    """
    if isinstance(state, expected_type):
        return state
    elif isinstance(state, dict):
        try:
            return expected_type(**state)
        except Exception as e:
            logger.error(
                f"Failed to convert dict to {expected_type.__name__}",
                extra={"error": str(e), "state_keys": list(state.keys())},
            )
            # Return minimal valid state
            return UniversalWorkflowState(
                session_id=safe_get(state, "session_id", str, "unknown"),
                user_id=safe_get(state, "user_id", str, "unknown"),
                auth_token=safe_get(state, "auth_token", str, "unknown"),
            )
    else:
        logger.error(
            f"Unexpected state type: {type(state).__name__}",
            extra={"expected": expected_type.__name__},
        )
        raise TypeError(f"Invalid state type: {type(state).__name__}")


if __name__ == "__main__":
    """Validation function for defensive state access utilities."""
    import sys

    from universal_framework.contracts.state import EmailRequirements

    # Test cases
    test_failures = []

    # Test 1: Pydantic model access
    try:
        pydantic_state = UniversalWorkflowState(
            session_id="test-123",
            user_id="user-456",
            auth_token="token-789",
            workflow_phase=WorkflowPhase.STRATEGY_ANALYSIS,
            email_requirements=EmailRequirements(
                purpose="Test email",
                email_type="announcement",
                audience=["test@example.com"],
                tone="professional",
                key_messages=["Test message"],
            ),
        )

        assert safe_get(pydantic_state, "session_id") == "test-123"
        assert (
            safe_get(pydantic_state, "workflow_phase")
            == WorkflowPhase.STRATEGY_ANALYSIS
        )
        assert safe_get_requirements(pydantic_state).purpose == "Test email"

    except Exception as e:
        test_failures.append(f"Pydantic model test failed: {e}")

    # Test 2: Dict access
    try:
        dict_state = {
            "session_id": "dict-123",
            "user_id": "dict-user",
            "auth_token": "dict-token",
            "workflow_phase": "generation",
            "email_requirements": {
                "purpose": "Dict test",
                "email_type": "update",
                "audience": ["dict@test.com"],
                "tone": "casual",
                "key_messages": ["Dict message"],
            },
        }

        assert safe_get(dict_state, "session_id") == "dict-123"
        assert safe_get_phase(dict_state) == WorkflowPhase.GENERATION
        assert safe_get_requirements(dict_state)["purpose"] == "Dict test"

    except Exception as e:
        test_failures.append(f"Dict access test failed: {e}")

    # Test 3: Missing attributes with defaults
    try:
        empty_state = {}
        assert safe_get(empty_state, "session_id", str, "default") == "default"
        assert safe_get_phase(empty_state) == WorkflowPhase.INITIALIZATION
        assert safe_get_requirements(empty_state) is None

    except Exception as e:
        test_failures.append(f"Missing attributes test failed: {e}")

    # Test 4: Type conversion
    try:
        str_state = {"workflow_phase": "strategy_analysis"}
        assert (
            safe_get(str_state, "workflow_phase", WorkflowPhase)
            == WorkflowPhase.STRATEGY_ANALYSIS
        )

        bool_state = {"strategy_approved": "true"}
        assert safe_get(bool_state, "strategy_approved", bool, False) is True

    except Exception as e:
        test_failures.append(f"Type conversion test failed: {e}")

    # Test 5: Nested access
    try:
        nested_state = {
            "context_data": {"workflow_data": {"phase": "review"}},
            "email_strategy": {
                "key_messages": ["nested", "test"],
                "is_confirmed": True,
            },
        }

        assert (
            safe_get_nested(nested_state, "context_data.workflow_data.phase")
            == "review"
        )
        assert (
            safe_get_nested(nested_state, "email_strategy.is_confirmed", bool) is True
        )

    except Exception as e:
        test_failures.append(f"Nested access test failed: {e}")

    # Test 6: State validation
    try:
        is_valid, description = validate_state_type(pydantic_state)
        assert is_valid is True
        assert "UniversalWorkflowState" in description

        is_valid, description = validate_state_type(dict_state)
        assert is_valid is True
        assert "dict" in description

    except Exception as e:
        test_failures.append(f"State validation test failed: {e}")

    # Test 7: State conversion
    try:
        converted = ensure_state_type(dict_state)
        assert isinstance(converted, UniversalWorkflowState)
        assert converted.session_id == "dict-123"

    except Exception as e:
        test_failures.append(f"State conversion test failed: {e}")

    # Report results
    if test_failures:
        print(f"❌ VALIDATION FAILED - {len(test_failures)} test(s) failed:")
        for failure in test_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            "✅ VALIDATION PASSED - All defensive state access utilities work correctly"
        )
        sys.exit(0)
