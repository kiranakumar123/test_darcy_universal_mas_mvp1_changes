from __future__ import annotations

from typing import Any

# Import from contracts module for consistency
from ..contracts.exceptions import StateValidationError


class ComplianceError(Exception):
    """Base compliance error for audit and policy violations."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}
        self.add_note(str(self.context))


class ComplianceViolationError(Exception):
    """Enterprise compliance requirement violation"""

    def __init__(self, message: str, violation_type: str, context: dict[str, Any]):
        super().__init__(message)
        self.violation_type = violation_type
        self.context = context
        self.add_note(f"Compliance violation: {violation_type} - {context}")


class UnauthorizedStateUpdateError(ComplianceViolationError):
    """Unauthorized state field modification attempt"""

    def __init__(
        self, agent: str, attempted_fields: list[str], authorized_fields: list[str]
    ):
        message = f"Agent {agent} unauthorized to modify {attempted_fields}"
        context = {
            "agent": agent,
            "attempted_fields": attempted_fields,
            "authorized_fields": authorized_fields,
            "security_event": True,
        }
        super().__init__(message, "unauthorized_state_update", context)


__all__ = [
    "ComplianceError",
    "ComplianceViolationError",
    "UnauthorizedStateUpdateError",
    "StateValidationError",
]
