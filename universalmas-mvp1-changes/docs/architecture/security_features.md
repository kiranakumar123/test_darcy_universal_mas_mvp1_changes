# Security Features

## Overview

The Universal Multi-Agent System Framework applies security controls across middleware, session management, compliance validation and CI/CD. Middleware layers handle HTTP security headers and JWT authentication while Redis-backed session storage enforces ownership checks. Sensitive data is sanitized before logging and enterprise audit logs capture security events.

## Authentication & Authorization

- **JWT Authentication** – `EnterpriseAuthMiddleware` validates Bearer tokens using a JWKS endpoint when configured, falling back to development bypass when no JWKS URL is provided【F:src/universal_framework/api/middleware.py†L69-L118】.
- **Authorization Matrix** – `AgentAuthorizationMatrix` defines which agents may update specific state fields, enforced by `FailClosedStateValidator` during state updates【F:src/universal_framework/compliance/authorization_matrix.py†L15-L67】【F:src/universal_framework/compliance/state_validator.py†L19-L87】.
- **Session Ownership** – `SessionValidator` verifies session ID format and checks ownership via `SessionStorage` before allowing actions【F:src/universal_framework/security/session_validator.py†L20-L68】【F:src/universal_framework/redis/session_storage.py†L87-L145】.

## Data Protection

- **HMAC Session IDs** – `create_user_namespaced_session_id` derives per-user session identifiers using SHA‑256 HMAC and `SESSION_SECRET_KEY` environment variable【F:src/universal_framework/security/session_validator.py†L69-L92】.
- **PII Redaction** – `PrivacySafeLogger` uses `PIIDetector` to hash session IDs and redact emails, phone numbers and other PII from logs【F:src/universal_framework/compliance/privacy_logger.py†L1-L63】【F:src/universal_framework/compliance/pii_detector.py†L1-L57】.
- **Sanitized Logging** – `sanitize_for_logging` removes tokens and passwords from Redis command logs【F:src/universal_framework/contracts/redis/validation.py†L236-L249】.
- **Template Validation** – `TemplateStore` rejects templates containing `<script>` or other dangerous patterns【F:src/universal_framework/templates/template_store.py†L153-L166】.
- **Environment Secrets** – `.env.example` documents secret variables such as `JWT_SECRET_KEY` and is excluded by `.gitignore`【F:.gitignore†L96-L104】【F:.env.example†L15-L21】.

## Input Validation & Output Escaping

- **State Validation** – `FailClosedStateValidator` enforces business rules and FSM transitions before state changes are accepted, raising exceptions on violations【F:src/universal_framework/compliance/state_validator.py†L19-L122】【F:src/universal_framework/compliance/state_validator.py†L123-L199】.
- **Session ID Format** – Invalid session identifiers produce HTTP 400 responses in `/workflow/execute`【F:src/universal_framework/api/routes/workflow.py†L223-L230】.

## Session & Token Security

- **Session TTL and Storage** – `SessionStorage` stores session metadata in Redis with a 24‑hour TTL and validates ownership on access【F:src/universal_framework/redis/session_storage.py†L21-L76】【F:src/universal_framework/redis/session_storage.py†L87-L145】.
- **Graceful Degradation** – When Redis is unavailable, behavior depends on `REDIS_GRACEFUL_DEGRADATION` and environment. Production denies validation failures while development/staging allow them【F:src/universal_framework/redis/session_storage.py†L221-L315】.
- **JWT Error Handling** – Expired or invalid tokens return 401 with descriptive details【F:src/universal_framework/api/middleware.py†L105-L149】.

## Transport Security

- **Security Headers** – `SecurityMiddleware` adds `X-Content-Type-Options`, `X-Frame-Options` and `X-XSS-Protection` headers to all responses【F:src/universal_framework/api/middleware.py†L50-L67】.
- **CORS Configuration** – `CORSMiddleware` currently allows all origins but includes a note to restrict in production【F:src/universal_framework/api/main.py†L63-L71】.
- **Redis TLS** – The configuration supports `rediss://` URLs for encrypted Redis connections though no enforcement is implemented【F:src/universal_framework/config/workflow_config.py†L18-L38】.

## Dependency & Supply Chain Security

- **Automated Scans** – CI runs `bandit` and `safety` to detect insecure code and vulnerable packages【F:.github/workflows/ci.yml†L108-L137】【F:.github/workflows/security.yml†L18-L27】.
- **Dependabot** – Weekly updates for pip and Docker images ensure dependencies stay patched【F:.github/dependabot.yml†L1-L21】.

## Infrastructure & Network Protections

- **Container Hardening** – Docker images run as a non‑root `universalframework` user and include health checks【F:Dockerfile†L14-L38】.
- **Session Isolation** – `RedisKeyManager` namespaces keys by environment and can hash identifiers to avoid exposing raw IDs【F:src/universal_framework/redis/key_manager.py†L20-L118】【F:src/universal_framework/redis/key_manager.py†L119-L176】.
- **CSP / HSTS** – No content security policy or HSTS configuration is present.

## CI/CD & Secrets Management

- **GitHub Actions** – Workflow files define separate jobs for quality gates, tests and compliance, running on Ubuntu runners with strict timeouts【F:.github/workflows/ci.yml†L1-L159】.
- **Secret Variables** – Secrets such as API keys are expected via environment variables and not stored in the repository. Example values are provided in `.env.example` which is ignored by Git【F:.env.example†L1-L28】【F:.gitignore†L96-L104】.

## Security Logging & Monitoring

- **Enterprise Audit Logs** – `EnterpriseAuditManager` logs security events and correlates them with LangSmith traces for monitoring【F:src/universal_framework/observability/enterprise_audit.py†L715-L748】.
- **Structured Logging** – `UniversalFrameworkLogger` warns when logging overhead exceeds 5 ms, ensuring logs do not harm performance while preserving privacy via `PrivacySafeLogger`【F:src/universal_framework/observability/unified_logger.py†L20-L84】【F:src/universal_framework/observability/unified_logger.py†L180-L241】.

## Known Gaps or TODOs

- **CORS Restrictions** – The API currently allows all origins. Production environments should restrict `allow_origins` and potentially enable HSTS.
- **Token Refresh** – No refresh or revocation strategy is implemented for JWTs.
- **HTTPS Enforcement** – The repository does not enforce HTTPS or set HSTS headers.
- **Cookie Security** – Sessions are not cookie-based; any future cookie usage should include `Secure` and `HttpOnly` flags.
