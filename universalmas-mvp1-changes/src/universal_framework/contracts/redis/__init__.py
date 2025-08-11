"""
Enterprise Redis Session Contracts
==================================

Schema-first design for Universal Multi-Agent Framework session management.
Follows enterprise best practices from LangChain, Semantic Kernel, and AutoGen.

Key Principles:
- JSON Schema validation for all data
- Hierarchical key naming with versioning
- Centralized validation and serialization
- Contract versioning with migration support
- Enterprise security and compliance
"""

from .interfaces import (
    MessageStoreInterface,
    RedisConnectionInterface,
    RedisSessionManagerInterface,
    SessionDataInterface,
)
from .key_manager import (
    RedisKeyManager,
    SessionKeyBuilder,
    get_message_key,
    get_session_key,
)
from .validation import (
    SchemaValidator,
    SessionValidator,
    validate_message_data,
    validate_session_data,
)

__all__ = [
    # Interfaces
    "RedisSessionManagerInterface",
    "RedisConnectionInterface",
    "SessionDataInterface",
    "MessageStoreInterface",
    # Validation
    "SessionValidator",
    "SchemaValidator",
    "validate_session_data",
    "validate_message_data",
    # Key Management
    "RedisKeyManager",
    "SessionKeyBuilder",
    "get_session_key",
    "get_message_key",
]

# Contract Version (increment for breaking changes)
CONTRACT_VERSION = "1.0.0"
SCHEMA_VERSION = 1
