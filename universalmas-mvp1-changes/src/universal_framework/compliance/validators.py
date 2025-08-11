from __future__ import annotations

import ast
import inspect
from collections.abc import Callable
from typing import Any


class ContractViolationError(Exception):
    """Raised when contract validation fails."""


class ContractComplianceValidator:
    """Static analysis utilities for contract adherence."""

    @staticmethod
    def validate_contract_usage(code_path: str) -> list[str]:
        violations: list[str] = []
        with open(code_path, encoding="utf-8") as file:
            tree = ast.parse(file.read())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") == "execute_command"
            ):
                violations.append(f"Direct Redis call at line {node.lineno}")
        return violations


def enforce_contract(interface_class: type) -> Callable[[type], type]:
    """Class decorator enforcing interface implementation."""

    def decorator(cls: type) -> type:
        if not issubclass(cls, interface_class):
            raise ContractViolationError(
                f"{cls.__name__} must implement {interface_class.__name__}"
            )
        for name in dir(interface_class):
            if name.startswith("_"):
                continue
            interface_method = getattr(interface_class, name, None)
            impl_method = getattr(cls, name, None)
            if callable(interface_method) and callable(impl_method):
                _validate_method_signature(impl_method, interface_method)
        return cls

    return decorator


def _validate_method_signature(
    method: Callable[..., Any], interface_method: Callable[..., Any]
) -> None:
    """Validate method signature matches interface."""
    if inspect.signature(method) != inspect.signature(interface_method):
        raise ContractViolationError(f"Method signature mismatch: {method.__name__}")
