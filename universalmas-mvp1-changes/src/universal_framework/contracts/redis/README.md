# Redis Session Contracts Documentation

## Overview

This module provides enterprise-grade contracts for Redis session management in the Universal Multi-Agent Framework. It follows schema-first design principles and enterprise best practices from LangChain, Semantic Kernel, and AutoGen.

## Key Principles

1. **Schema-First Design**: All data validated against JSON Schema
2. **Hierarchical Key Naming**: Prevents collisions, enables efficient scanning
3. **Centralized Validation**: One source of truth for data integrity
4. **Contract Versioning**: Safe evolution with migration support
5. **Enterprise Security**: No sensitive data logging, sanitization

## Quick Start

```python
from universal_framework.contracts.redis import (
    validate_session_data,
    get_session_key,
    KeyType
)

# Validate data before storage
errors = validate_session_data(session_data)
if not errors:
    key = get_session_key(KeyType.SESSION_DATA, session_id)
    # Store to Redis...

## Key Naming Convention

All Redis keys follow the pattern:
```
<scope>:<system>:<environment>:<type>:<identifier>:v<version>[:<suffix>]
```

Examples:
- `session:universal_framework:prod:messages:abc123:v1`
- `user:universal_framework:prod:hash456:v1:sessions`
- `global:universal_framework:prod:stats:daily:v1`

## Schema Versions

- **v1.0.0**: Initial schema with session data, messages, metadata
- **Future versions**: Will include migration paths

## Contract Evolution

1. Update JSON schema in `schemas.json`
2. Increment version numbers
3. Create migration in `migrations.py`
4. Update validation logic
5. Test backward compatibility

## Security Guidelines

- Never log sensitive data (passwords, tokens, personal info)
- Use sanitization functions for logging
- Implement proper key namespacing
- Follow GDPR TTL requirements (24 hours default)

## Testing

All contract changes must include:
- Schema validation tests
- Migration tests (if applicable)
- Security sanitization tests
- Key naming compliance tests

## Support

For questions or contract change requests, contact the Universal Framework team.
```
