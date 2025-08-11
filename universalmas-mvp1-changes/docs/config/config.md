# Configuration Reference

## Table of Contents

- [Overview](#overview)
- [Safe Mode Configuration](#safe-mode-configuration)
- [Environment Variables](#environment-variables)
- [Static Configuration Files](#static-configuration-files)

## Related Guides

- **[Safe Mode Guide](safe-mode.md)** - Complete guide to safe mode operation, feature flags, and debugging workflows
- **[Safe Mode Implementation](safe-mode-implementation.md)** - Technical implementation details for developers

## Overview

The Universal Multi-Agent System Framework relies primarily on environment variables for configuration. Optional TOML files under `config/` provide defaults that can be overridden by the environment. Configuration is loaded through lightweight helper functions without a dedicated framework. The `python-dotenv` dependency is included for `.env` file support, and TOML files are parsed via Python's `tomllib`.

## Safe Mode Configuration

For development and debugging, the framework includes a comprehensive **Safe Mode** system that provides graceful degradation when enterprise features encounter issues. See the [Safe Mode Guide](safe-mode.md) for detailed information on:

- Feature flag configuration
- Safe fallback implementations  
- Progressive feature enablement
- Production vs development workflows

**Quick Start**: Set `SAFE_MODE=true` to enable debugging mode with enterprise features disabled.

## Environment Variables

| Variable | Required? | Default Value | Used In | Description |
| --- | --- | --- | --- | --- |
| ENVIRONMENT | No | `development` | `environment.py`, `session_storage.py` | Runtime environment name. Influences LangSmith config and Redis keys. |
| DEBUG | No | `true` | `.env.example` | Development mode flag. Not read by code. |
| API_HOST | No | `0.0.0.0` | `.env.example` | Host for local API server (unused in code). |
| API_PORT | No | `8000` | `.env.example` | Port for local API server (unused in code). |
| REDIS_HOST | No | `localhost` | `workflow_config.py` | Redis hostname when not using `REDIS_URL`. |
| REDIS_PORT | No | `6379` | `workflow_config.py` | Redis port number. |
| REDIS_DB | No | `0` | `workflow_config.py` | Redis database index. |
| REDIS_PASSWORD | No | *(empty)* | `workflow_config.py` | Password for Redis connection. |
| REDIS_URL | No | – | `workflow_config.py` | Complete Redis connection string. Overrides host/port/db. |
| REDIS_TTL_HOURS | No | `24` | `workflow_config.py` | Default TTL for Redis keys (hours). |
| REDIS_GRACEFUL_DEGRADATION | No | `true` | `session_storage.py` | Allow in-memory fallback when Redis is unavailable. |
| ENABLE_REDIS_OPTIMIZATION | No | `false` | `workflow_config.py` | Toggle Redis-based optimizations. |
| ENABLE_DEBUG | No | `false` | `workflow_config.py` | Enables debug features and relaxes JWT requirement. |
| ENABLE_PARALLEL_PROCESSING | No | `false` | `workflow_config.py` | Allow parallel agent execution. |
| ENABLE_METRICS | No | `true` | `workflow_config.py` | Enable Prometheus metrics. |
| METRICS_PORT | No | `9090` | `.env.example` | Metrics server port (unused in code). |
| LOG_LEVEL | No | `INFO` | `workflow_config.py` | Logging level. |
| LOG_FORMAT | No | `json` | `.env.example` | Preferred log format (unused in code). |
| JWT_SECRET_KEY | Conditional | – | `workflow_config.py` | Secret for signing JWT tokens. Required in non-debug mode. |
| JWT_ALGORITHM | No | `HS256` | `.env.example` | JWT signing algorithm (unused). |
| JWT_EXPIRE_MINUTES | No | `1440` | `.env.example` | JWT token lifetime in minutes (unused). |
| JWT_JWKS_URL | No | – | `api/middleware.py` | URL to fetch JWKS for token verification. |
| JWT_ISSUER | No | – | `api/middleware.py` | Expected JWT issuer. |
| JWT_AUDIENCE | No | – | `api/middleware.py` | Expected JWT audience. |
| SESSION_SECRET_KEY | No | `dev_secret` | `session_validator.py` | Key for session ID hashing. |
| SESSION_TIMEOUT_HOURS | No | `8` | `workflow_config.py` | Web session timeout. |
| ENABLE_AUTH_VALIDATION | No | `true` | `workflow_config.py` | Enforce JWT validation on requests. |
| MAX_EXECUTION_TIME_SECONDS | No | `30` | `workflow_config.py` | Workflow execution timeout. |
| AGENT_TIMEOUT_SECONDS | No | `5` | `workflow_config.py` | Individual agent timeout. |
| MAX_CONCURRENT_SESSIONS | No | `1000` | `workflow_config.py` | Concurrent session limit. |
| SESSION_CACHE_SIZE | No | `100` | `workflow_config.py` | In-memory session cache size. |
| SESSION_CLEANUP_INTERVAL | No | `3600` | `workflow_config.py` | Background cleanup interval (seconds). |
| MAX_SESSION_AGE_HOURS | No | `24` | `workflow_config.py`, `session_manager.py` | Maximum session lifetime. |
| OPENAI_API_KEY | Yes (for LLM) | – | `providers.py`, `environment.py` | OpenAI API key for model access. |
| OPENAI_MODEL | No | `gpt-4` | `providers.py`, `environment.py` | Default model name. |
| TEMPERATURE | No | `0.1` | `providers.py`, `environment.py` | Model sampling temperature. |
| MAX_TOKENS | No | `2000` | `providers.py`, `environment.py` | Max tokens per response. |
| STRATEGY_TIMEOUT_SECONDS | No | `10` | `providers.py` | Timeout for strategy generation. |
| MAX_RETRIES | No | `2` | `providers.py` | Retry attempts for LLM calls. |
| FALLBACK_ENABLED | No | `true` | `providers.py` | Enable fallback model logic. |
| **SAFE_MODE** | **No** | **`true`** | **Safe Mode System** | **Master toggle for safe mode (enables graceful degradation by default).** |
| **ENTERPRISE_FEATURES** | **No** | **`false`** | **Safe Mode System** | **Master toggle for all enterprise functionality (disabled by default).** |
| **ENTERPRISE_AUTH_MIDDLEWARE** | **No** | **`false`** | **Safe Mode System** | **Enable enterprise authentication middleware.** |
| **ENTERPRISE_AUDIT_VALIDATION** | **No** | **`false`** | **Safe Mode System** | **Enable full audit compliance validation.** |
| **LANGSMITH_TRACING** | **No** | **`false`** | **Safe Mode System** | **Enable LangSmith observability integration.** |
| **PII_REDACTION** | **No** | **`false`** | **Safe Mode System** | **Enable privacy-safe logging with PII detection.** |
| **AUTHORIZATION_MATRIX** | **No** | **`false`** | **Safe Mode System** | **Enable field-level access control enforcement.** |
| **COMPLIANCE_MONITORING** | **No** | **`false`** | **Safe Mode System** | **Enable SOC2/GDPR compliance tracking.** |
| LANGSMITH_API_KEY | No | – | `environment.py` | Enables LangSmith tracing when set. |
| LANGCHAIN_PROJECT | No | `universal-framework` | `environment.py` | Project name for LangSmith traces. |
| LANGCHAIN_TRACING_V2 | No | `false` (auto-enabled with `LANGSMITH_API_KEY`) | `environment.py`, `.env.example` | Toggle LangSmith V2 tracing. |
| LANGCHAIN_API_KEY | No | – | `.env.example` | API key for LangSmith (optional). |
| BOUNDARYML_API_KEY | No | – | `.env.example` | BoundaryML integration key (unused). |
| DD_API_KEY / DATADOG_API_KEY | No | – | `performance.py` | Enable DataDog metrics client. |
| COMPLIANCE_HASH_SALT | No | `default_enterprise_salt` | `compliance_loader.py` | Salt used when hashing audit data. |
| ENTERPRISE_COMPLIANCE_ENABLED | No | – | `compliance_loader.py` | Override to enable/disable compliance features. |
| DATABASE_URL | No | `sqlite:///./universal_framework.db` | `.env.example` | Database connection string (unused). |
| OPENAI_TEST_API_KEY | No | – | `tests/conftest.py` | Real OpenAI key for integration tests. |

## Static Configuration Files

### `config/llm.toml`
TOML file providing default LLM settings. Fields include API key reference, model name, temperature, and retry policy. See lines 1‑25 for full structure:
```
[llm]
openai_api_key = "${OPENAI_API_KEY}"
model_name = "gpt-4"
temperature = 0.1
max_tokens = 2000

[agent_defaults]
max_iterations = 3
max_execution_time = 30.0
handle_parsing_errors = true

[logging]
level = "INFO"
format = "json"
structured = true

[strategy_generation]
timeout_seconds = 10
max_retries = 2
fallback_enabled = true

[prompts.strategy]
system_message = "You are an expert email communication strategist."
temperature = 0.7
max_tokens = 1500
```
Used by `get_llm_config_from_toml` in `toml_loader.py`.

### `config/langsmith.toml`
Defines LangSmith enterprise, performance, and environment-specific options. Key sections cover retry behavior, tracing capture, and cost tracking. See lines 1‑65 for full structure:
```
[langsmith.enterprise]
max_retries = 3
retry_backoff_factor = 2.0
max_retry_backoff = 60.0
connection_timeout_seconds = 30.0

[langsmith.performance]
max_trace_overhead_ms = 10.0
sampling_rate = 1.0
batch_size = 100
batch_timeout_seconds = 5.0
failure_threshold = 5
recovery_timeout_seconds = 60.0

[langsmith.tool_tracing]
capture_tool_arguments = true
capture_tool_outputs = true
max_argument_length = 1000
max_output_length = 2000
redact_sensitive_tool_data = true

[langsmith.reasoning_capture]
capture_scratchpad = true
capture_intermediate_steps = true
max_reasoning_steps = 10
reasoning_preview_length = 200
include_confidence_scores = true

[langsmith.cost_tracking]
track_token_usage = true
track_cost_attribution = true
cost_alert_threshold_usd = 10.0
efficiency_monitoring = true
per_agent_cost_breakdown = true

[langsmith.environments.development]
sampling_rate = 1.0
failure_threshold = 10
max_trace_overhead_ms = 50.0
capture_tool_arguments = true
capture_scratchpad = true
track_cost_attribution = true

[langsmith.environments.staging]
sampling_rate = 0.5
failure_threshold = 5
max_trace_overhead_ms = 20.0
capture_tool_arguments = true
capture_scratchpad = false
track_cost_attribution = true

[langsmith.environments.production]
sampling_rate = 0.1
failure_threshold = 3
max_trace_overhead_ms = 5.0
capture_tool_arguments = false
capture_scratchpad = false
track_cost_attribution = true

[langsmith.compliance]
privacy_level = "high"
use_existing_pii_detector = true
use_existing_privacy_logger = true
redact_tool_arguments = true
redact_reasoning_content = true
```
Loaded by `get_langsmith_config` in `environment.py`.

### `config/compliance.toml`
Enterprise compliance defaults including redaction patterns and audit settings. Environment variables may override `audit_settings.hash_salt` and `enterprise_compliance.enabled`. See lines 1‑24 for example contents:
```
[enterprise_compliance]
enabled = true
fail_closed_validation = true
audit_retention_hours = 168
gdpr_compliant_logging = true

[redaction_config]
email_pattern = "***@***.***"
phone_pattern = "***-***-****"
ssn_pattern = "***-**-****"

[audit_settings]
hash_salt = "${COMPLIANCE_HASH_SALT}"
log_level = "INFO"
enterprise_logging = true

[authorization_matrix]
strict_enforcement = true
unknown_agent_policy = "deny"

[performance]
validation_timeout_ms = 50
max_audit_entries_per_session = 1000
compliance_monitoring = true
```
Processed by `load_compliance_config`.

## Runtime Configuration Logic

- `create_llm_config` in `factory.py` loads the LLM configuration from `llm.toml` or environment variables with fallback ordering. If no configuration is found, it raises an error prompting the user to set `OPENAI_API_KEY` or create `config/llm.toml`.
- `get_langsmith_config` merges `langsmith.toml` settings with environment variables based on the current `ENVIRONMENT` value and enables tracing when `LANGSMITH_API_KEY` is present.
- `WorkflowConfig` reads all its fields from environment variables at instantiation time and exposes a `validate()` method to check numeric ranges and required values.
- `SessionStorage` and `SessionManagerImpl` use the `ENVIRONMENT` variable to namespace Redis keys and optionally degrade gracefully based on `REDIS_GRACEFUL_DEGRADATION`.
- `EnterpriseAuthMiddleware` fetches JWKS configuration from environment variables and bypasses validation when running in development with no JWKS URL.

## Deployment & Secrets

Sensitive values such as `OPENAI_API_KEY`, `JWT_SECRET_KEY`, and `COMPLIANCE_HASH_SALT` should be provided through environment variables or a secrets manager. Example environment templates are provided in `.env.example` and generated by `scripts/setup.sh`. In production deployments you must supply real secrets and disable `ENABLE_DEBUG` to enforce JWT validation.

## CLI Flags and Build Parameters

- The project is typically started via `uvicorn` (`docker-compose.yml` uses `uvicorn universal_framework.api.main:app --host 0.0.0.0 --port 8000 --reload`). Host and port may be adjusted using the `API_HOST` and `API_PORT` environment variables though the code does not read them directly.
- Docker images are built with the included `Dockerfile` and `Dockerfile.dev`. `docker-compose.yml` sets `ENVIRONMENT=development` for the main container.
- `scripts/setup.sh` creates a `.env` file and validates the development environment.

