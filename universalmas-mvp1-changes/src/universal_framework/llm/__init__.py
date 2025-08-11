"""LLM integration module with dependency validation."""

import importlib


def check_langchain_openai() -> bool:
    """Check if langchain-openai is available."""
    try:
        importlib.import_module("langchain_openai")
        return True
    except ImportError:
        return False


# Conditional imports to prevent import errors
if check_langchain_openai():
    from .providers import (
        LLMConfig,
        LLMProvider,
        OpenAIProvider,
        create_default_provider,
    )
    from .tools import EmailValidationTool, RequirementsExtractionTool, StateAccessTool

    __all__ = [
        "OpenAIProvider",
        "LLMConfig",
        "LLMProvider",
        "EmailValidationTool",
        "RequirementsExtractionTool",
        "StateAccessTool",
        "create_default_provider",
    ]
else:
    # Fallback when dependencies missing
    import warnings

    warnings.warn(
        "langchain-openai not found. Install with: pip install langchain-openai",
        ImportWarning,
        stacklevel=2,
    )

    __all__ = []


def get_missing_dependencies() -> list[str]:
    """Get list of missing required dependencies."""
    missing = []

    if importlib.util.find_spec("langchain") is None:
        missing.append("langchain")
    if importlib.util.find_spec("langchain_openai") is None:
        missing.append("langchain-openai")
    if importlib.util.find_spec("langchain_community") is None:
        missing.append("langchain-community")

    return missing
