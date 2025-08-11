# Architecture Overview

## System Overview

The **Universal Multi-Agent System Framework** is a Python 3.11 based platform for building and orchestrating multi‑agent workflows.  It exposes a FastAPI application and provides utilities for session management, compliance enforcement, logging, and language model integration.  Workflows are defined through LangGraph `StateGraph` patterns, with agents implemented as modular nodes.  Redis is used for session storage, and optional integrations include OpenAI providers, LangSmith tracing, and performance monitoring.

**Default Behavior**: The framework operates in **Safe Mode** by default when no environment variables are configured, providing graceful degradation and core functionality while enterprise features remain disabled until explicitly enabled.

## Component Breakdown

### Agents (`src/universal_framework/agents`)
Agents implement domain‑specific logic such as requirement collection, strategy generation, confirmation handling, and email generation. They can run as real LangChain agents or simulations for testing.

### API (`src/universal_framework/api`)
FastAPI application exposing workflow execution and health endpoints.  Includes middleware for security, logging, and tracing.  `main.py` initializes the application and registers routes.

### Compliance (`src/universal_framework/compliance`)
Validation helpers, privacy logging, and audit management enforcing enterprise compliance policies.

### Config (`src/universal_framework/config` and `/config`)
TOML configuration loaders and environment helpers. Root `config/` directory contains default `compliance.toml`, `langsmith.toml`, and `llm.toml` files.

### Contracts (`src/universal_framework/contracts`)
Typed dataclasses and exceptions defining the canonical workflow state, messages, and node interfaces used across the framework.

### LLM Providers (`src/universal_framework/llm`)
Abstractions for language model interaction, including an OpenAI provider and reusable tool definitions.

### Observability (`src/universal_framework/observability`)
Logging configuration, tracing utilities, and metrics collection. Includes LangSmith and OpenTelemetry middleware.

### Redis Integration (`src/universal_framework/redis`)
Connection helpers, key management, session managers, and storage adapters built on `redis`/`aioredis`.

### Security (`src/universal_framework/security`)
Session validation utilities ensuring authorized access and session ownership.

### Session (`src/universal_framework/session`)
Wrapper logic around session managers and contracts for managing workflow sessions.

### Templates (`src/universal_framework/templates`)
Template storage and selection helpers for email/content generation.

### Utils (`src/universal_framework/utils`)
General utilities such as session logging and template selection logic.

### Workflow (`src/universal_framework/workflow`)
Workflow builder, orchestrator, routing, and node definitions implementing LangGraph patterns.  Provides factory functions like `create_streamlined_workflow`.

### Tests (`tests`)
Pytest suite covering compliance, contracts, integration scenarios, observability, Redis functions, and more.

### Scripts (`scripts`)
CI and setup scripts including performance checks, compliance validation, environment setup, and Docker validation.

## Directory Structure

```text
./
├── CHANGELOG.md
├── Dockerfile
├── Dockerfile.dev
├── README.md
├── config/
│   ├── compliance.toml
│   ├── langsmith.toml
│   └── llm.toml
├── docker-compose.yml
├── docs/
│   ├── README.md
│   ├── architecture/
│   │   ├── email_workflow_architecture.md
│   │   └── scaling_guide.md
│   ├── compliance/
│   │   ├── MIGRATION_GUIDE.md
│   │   └── compliance_patterns.md
│   ├── langgraph/
│   │   ├── index.md
│   │   ├── README.md
│   │   ├── setup_guide.md
│   │   ├── usage_guide.md
│   │   └── universal_workflow.mmd
│   └── specifications/
│       └── Product Requirements Document.md
├── fixtures/
│   └── __init__.py
├── pyproject.toml
├── requirements-dev.txt
├── requirements.txt
├── scripts/
│   ├── ci/
│   │   ├── performance_check.py
│   │   ├── validate_compliance.py
│   │   └── validate_python311_compatibility.py
│   ├── setup.sh
│   └── validate_environment.sh
├── src/
│   ├── universal_framework/
│   │   ├── __init__.py
│   │   ├── agents/
│   │   ├── api/
│   │   ├── compliance/
│   │   ├── config/
│   │   ├── contracts/
│   │   ├── llm/
│   │   ├── monitoring/
│   │   ├── nodes/
│   │   ├── observability/
│   │   ├── redis/
│   │   ├── security/
│   │   ├── session/
│   │   ├── templates/
│   │   ├── ui/
│   │   ├── utils/
│   │   └── workflow/
│   └── universal_framework.egg-info/
│       ├── PKG-INFO
│       ├── SOURCES.txt
│       ├── dependency_links.txt
│       └── top_level.txt
└── tests/
    ├── __init__.py
    ├── compliance/
    │   ├── __init__.py
    │   ├── test_audit_compliance.py
    │   ├── test_classification_manager.py
    │   ├── test_compliance_patterns.py
    │   ├── test_pii_detector.py
    │   ├── test_privacy_logger.py
    │   └── test_state_validator.py
    ├── conftest.py
    ├── contracts/
    │   └── test_exceptions.py
    ├── fixtures/
    │   └── __init__.py
    ├── integration/
    │   ├── test_exception_handling.py
    │   ├── test_real_agent_workflow.py
    │   └── test_session_security_api.py
    ├── observability/
    │   ├── __init__.py
    │   ├── test_enterprise_audit_langsmith.py
    │   ├── test_langsmith_middleware.py
    │   ├── test_trace_correlation.py
    │   └── test_unified_logging.py
    ├── performance/
    │   └── test_strategy_agent_performance.py
    ├── redis/
    │   ├── test_backward_compatibility.py
    │   ├── test_graceful_degradation.py
    │   ├── test_redis_key_manager.py
    │   ├── test_session_storage_integration.py
    │   └── test_session_storage_key_manager.py
    ├── security/
    │   ├── test_sanitization_removal.py
    │   └── test_session_ownership.py
    ├── templates/
    │   └── test_template_store.py
    ├── test_environment.py
    ├── universal_framework/
    │   ├── agents/
    │   ├── contracts/
    │   ├── llm/
    │   ├── nodes/
    │   ├── observability/
    │   └── workflow/
    ├── utils/
    │   └── test_template_selector.py
    └── validation/
        ├── __init__.py
        ├── test_config_completeness.py
        └── test_interface_compliance.py
```

### Folder Purpose
- **config/** – Default configuration files loaded by the framework.
- **docs/** – Project documentation including architecture guides, compliance notes, and LangGraph Studio integration guides.
- **fixtures/** – [Undocumented: Purpose not clear]
- **scripts/** – Helper scripts for CI, environment setup, and validation.
- **src/** – Source code for the framework.
- **tests/** – Pytest suite covering framework components.

## Naming Conventions

- **Files & Directories**: `snake_case` for Python modules and directories.
- **Classes**: `CamelCase` naming in code.
- **Tests**: Files start with `test_` and reside under `tests/` mirroring the source layout.
- **Configuration**: TOML files named by purpose (`llm.toml`, `langsmith.toml`).
- **Scripts**: Bash or Python scripts within `scripts/` use descriptive names with underscores.

## Integration Notes

- **Configuration Files**: Located in the root `config/` directory and loaded by modules in `src/universal_framework/config`.
- **Build & Deployment**: `Dockerfile` and `Dockerfile.dev` define production and development images. `docker-compose.yml` runs the API and Redis for local development.
- **CI Scripts**: `scripts/ci/` contains performance and compliance validation used in pipelines.
- **Entry Points**: The FastAPI application starts from `src/universal_framework/api/main.py`. Package initialization occurs in `src/universal_framework/__init__.py`.
- **Environment Requirements**: Python 3.11+, dependencies specified in `requirements.txt` and `requirements-dev.txt`.

## Diagrams

No architecture diagrams are stored in the repository. A component diagram illustrating API, agent nodes, Redis session storage, and observability components would aid new contributors.
