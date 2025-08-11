# AGENTS.md: Instructions for Universal Multi-Agent System Agents

This document outlines the foundational plan and standards for the **Universal Multi-Agent System Framework** project.
As the project architect, you provide vision and guidance; developers will follow this playbook for implementation, extension, and maintenance.

---

## 1. Project Vision

* **Project Name:** Universal Multi-Agent System Framework

* **Core Idea:**
  Build an enterprise-grade, pluggable, and extensible framework for orchestrating multi-agent workflows across any business use case. The framework enforces strict workflow, audit, and compliance standards, while enabling rapid configuration for new domains (change management, document generation, analytics, etc.).

* **Key Feature to Build First:**
  Implement the universal workflow core, including:

  * Universal state model (`UniversalWorkflowState`)
  * FSM-enforced multi-phase workflow
  * Agent role registry for all workflow phases
  * Edge-based conditional routing
  * Pluggable agent node system with audit, persona adaptation, and enterprise controls

---

## 2. Technology Stack

This project will be built **exclusively** with the following technologies.
**Do not use alternatives without explicit approval.**

* **Programming Language:** Python 3.11+
* **Primary Frameworks/Libraries:**

  * [LangChain](https://github.com/langchain-ai/langchain) (core agent/message abstractions)
  * [LangGraph](https://github.com/langchain-ai/langgraph) (workflow graph and FSM orchestration)
  * [LangSmith](https://smith.langchain.com/) (tracing, experiment management, agent observability)
  * [Redis](https://redis.io/) (multi-session state, checkpointing, production deployment)
  * \[asyncio] (asynchronous workflow and agent operations)
* **Ready for Integration (API Connectors Prepped):**

  * [Qdrant](https://qdrant.tech/) (vector database for RAG and agent memory)
  * [Datadog](https://www.datadoghq.com/) (logging, monitoring, alerting, APM)
  * [Kubernetes](https://kubernetes.io/) (deployment and scaling; all services must be containerized and compatible with K8s manifests)
* **Testing Framework:** pytest
* **Code Style:** Strict adherence to [PEP 8](https://peps.python.org/pep-0008/). All code must be auto-formatted using [Black](https://github.com/psf/black).

---

## 3. Development Philosophy & Structure

* **🧹 TEMPORARY FILE HYGIENE (CRITICAL):**
  
  **Always use the `.temp/` folder for temporary files during development:**
  - Analysis scripts → `temp_analysis_[description].py`
  - Validation scripts → `temp_validate_[description].py`
  - Summary files → `temp_summary_[description].md`
  - Debug outputs → `temp_debug_[description]_[date].json`
  
  **MANDATORY CLEANUP CHECKLIST** - Verify before completing any task:
  - [ ] Check `.temp/` folder for leftover files
  - [ ] Remove any temporary files from project root
  - [ ] Update CHANGELOG.md instead of creating summary files
  - [ ] Verify no `temp_*`, `*_summary*`, or `implementation_*` files in workspace root
  
  **If you create temporary files outside `.temp/`, you MUST clean them up before task completion.**

* **Test-Driven Development (TDD):**
  All new features and bug fixes must begin with a failing test. Write only enough code to make the test pass. Prioritize unit tests for agents, integration tests for workflows, and regression tests for error handling.

* **Enterprise Patterns:**

  * Enforce **FSM phase gates** and only allow progression if all required state/criteria are met.
  * **Audit** all agent execution and workflow transitions for compliance (all audits remain in Redis or memory unless otherwise specified).
  * Design all agent roles as **pluggable nodes** with configurable specialization.
  * Provide **error recovery, escalation, and rollback** for every workflow phase.
  * Support **global commands** (help, restart, go back, debug) at all phases.
  * Integrate **persona and context adaptation**—agent responses must match detected user tier and communication style.
  * Instrument all agent, workflow, and API interactions for **LangSmith tracing** (use `langsmith` decorators, session IDs, and experiment tags).

* **Directory Structure:**
  Please create the following initial directory structure:

  ```
  /
  ├── src/                         # Main framework and agent source code
  │   ├── __init__.py
  │   ├── agents/                  # All universal and use-case-specific agent implementations
  │   │   └── __init__.py
  │   ├── fsm/                     # FSM and workflow enforcement modules
  │   ├── orchestration/           # Workflow graph construction and routing logic
  │   ├── utils/                   # Helper functions (e.g., session, audit, persona)
  │   ├── integrations/            # API adapters for Qdrant, Datadog, Kubernetes
  │   └── config/                  # Use case configs, templates, and specialization logic
  ├── tests/                       # All tests
  │   └── __init__.py
  ├── docs/                        # Project documentation and architectural diagrams
  │   └── AGENTS.md                # (this file)
  ├── Dockerfile                   # For containerization
  ├── docker-compose.yml           # Multi-service orchestration (Redis, Qdrant, etc.)
  ├── README.md                    # Project README and onboarding
  └── pyproject.toml               # Project configuration and dependencies
  ```

---

## 4. Universal Agent Roles

* **Entry & Session Agents:**

  * `session_manager`, `context_initializer`, `objective_clarifier`, `security_guardian`
* **Discovery Agents:**

  * `conversation_orchestrator`, `requirement_analyst`, `context_researcher`, `stakeholder_mapper`, `constraint_identifier`, `scope_designer`
* **Analysis Agents:**

  * `data_analyst`, `option_evaluator`, `risk_assessor`, `impact_analyzer`, `feasibility_checker`, `recommendation_engine`
* **Generation Agents:**

  * `content_creator`, `structure_architect`, `style_adapter`, `template_engine`, `media_processor`, `integration_synthesizer`
* **Review Agents:**

  * `quality_validator`, `accuracy_checker`, `compliance_auditor`, `stakeholder_reviewer`, `bias_detector`, `improvement_suggester`
* **Delivery Agents:**

  * `packaging_manager`, `distribution_coordinator`, `presentation_optimizer`, `feedback_collector`, `iteration_manager`, `completion_specialist`
* **Global Handlers:**

  * `debug_controller`, `workflow_controller`, `checkpoint_navigator`, `command_router`, `progress_tracker`, `help_system`
* **Error & Recovery Agents:**

  * `failure_analyst`, `recovery_coordinator`, `fallback_manager`, `escalation_handler`, `dependency_resolver`, `performance_optimizer`

Each agent should be implemented as an **async class** exposing a standard interface, pluggable into the workflow.

---

## 5. Universal Workflow Phases

The FSM must enforce and audit the following workflow progression:

```
initialization → discovery → analysis → generation → review → delivery → completion
```

Each phase has strict data/criteria requirements, with explicit error handling, audit, and rollback.

---

## 6. Pluggability, Integrations & Specialization

* All business logic and use case specialization (e.g., OCM, document generation, analytics) is delivered via config injection. No hard-coding of use-case logic in the universal framework.
* New agent roles or deliverables must be registered in `src/config/` and thoroughly tested before deployment.
* **Qdrant, Datadog, and Kubernetes** integrations:

  * Implement `src/integrations/` adapters for Qdrant (vector storage/retrieval), Datadog (logging/metrics/APM), and Kubernetes (deployment, scaling, health checks).
  * These adapters should include full interface and API connection logic, with comprehensive unit/integration tests and mock endpoints for local testing.
  * Production deployments should require only environment variable configuration or secrets injection to go live.

---

## 7. Agent Implementation Standards

* **Async interface required** (all agents must support async invocation).
* **Input:** UniversalWorkflowState; **Output:** updated state or result object.
* All agent logic must be modular and testable in isolation.
* Log every agent execution to the audit trail, including errors, phase, and node info (stored in Redis by default).
* Use only the allowed libraries and configuration patterns described above.
* **Instrument all workflow and agent events using LangSmith** (tracing decorators, run IDs, experiment tags).

---

## Defensive Programming for LangGraph/LangChain Orchestration

### Why Defensive Programming Is Required

LangGraph and LangChain orchestration frameworks may convert Pydantic `BaseModel` state objects to dictionaries during workflow execution. This is an expected and documented behavior in LangGraph. Direct attribute access (e.g., `state.workflow_phase`) will fail with `'dict' object has no attribute ...'` errors if the state has been converted to a dict.

### Official Pattern

Always use defensive programming when accessing workflow state attributes that may be converted to dicts:

```python
try:
    workflow_phase = state.workflow_phase
except AttributeError:
    workflow_phase = WorkflowPhase(state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value))
```

Or, for generic access:

```python
def get_state_value(state, key, default=None):
    return state.get(key, default) if isinstance(state, dict) else getattr(state, key, default)
```

### When to Apply
- Any time you access attributes on workflow state objects in orchestrators, routers, API endpoints, tracing, or message management modules.
- Any time you use LangGraph or LangChain orchestration and your state schema is a Pydantic model.
- Any time you see errors like `'dict' object has no attribute ...'` in workflow execution.

### Best Practices
- Always check for both attribute and dict access.
- Use `try/except AttributeError` or `hasattr` for safe access.
- Use the fallback value from the dict if the attribute is missing.
- Document this pattern in all orchestration-related modules.
- Reference this file in PRs and code reviews for LangGraph/LangChain orchestration.

### Example
```python
# Defensive access in orchestrator
try:
    current_phase = state.workflow_phase
except AttributeError:
    current_phase = WorkflowPhase(state.get("workflow_phase", WorkflowPhase.INITIALIZATION.value))
```

### Reference
- LangGraph documentation: "Currently, the output of the graph will NOT be an instance of a pydantic model"
- LangGraph prebuilt modules use this pattern for all state access

**Always use defensive programming for state access in LangGraph/LangChain orchestration.**

---

## 8. Use of the Templates File

The project contains a dedicated **templates file/directory** (`templates/`) which includes reference implementations, skeletons, and best-practice patterns for:

* **LangChain agents and chains**
* **LangGraph node and workflow patterns**
* **LangSmith tracing/instrumentation**
* **Integration and API adapters (e.g., for Qdrant, Datadog, Kubernetes)**
* **Other common enterprise utility modules**

### **Guidance:**

* Whenever a task, user story, or feature specification mentions a standard pattern, integration, or “template” component, **developers must begin by reviewing and using the corresponding entry from the templates file/directory**.
* These templates are intended as **the canonical foundation** for all new agent classes, nodes, integrations, and instrumented workflows, ensuring codebase consistency, upgradability, and rapid onboarding for new contributors.
* If a required template is missing, incomplete, or inapplicable, developers must document why and consult the project architect before creating custom solutions.

**Summary Table:**

| When to Use the Templates File                   | How to Proceed                                    |
| ------------------------------------------------ | ------------------------------------------------- |
| New agent class or workflow node                 | Start from provided LangChain/LangGraph templates |
| Adding tracing or experiment instrumentation     | Use LangSmith templates as baseline               |
| Implementing integrations (Qdrant, Datadog, K8s) | Use integration adapter templates                 |
| Creating utility, config, or helper modules      | Check for best-practice stubs/templates           |

**Location:**

* Templates are found in `docs/templates/`.

**Failure to use templates as a baseline must be justified and reviewed.**

## 9. Codex PR Submission Checklist

### **Modern Python Patterns**

* [ ] Use `match…case` for value/structural branching instead of `if…elif` ladders.
* [ ] Adopt Python 3.11+ features where beneficial:

  * `ExceptionGroup` and `except*` for handling multiple concurrent errors
  * Native `tomllib` for TOML parsing, not external libs (`tomli` etc.)
  * Type unions: `int | None` not `Optional[int]`
  * Use `Self` in method signatures when returning the same class (PEP 673)
  * Prefer keyword-only and positional-only arguments as needed.
* [ ] Use [PEP 695 type parameter syntax](https://peps.python.org/pep-0695/) for generic classes/functions if type generics are required.
* [ ] No usage of deprecated Python stdlib modules (e.g., `distutils`, `imp`, `cgi`, etc.).

---

### **Typing & Data Validation**

* [ ] All public functions/classes have complete type hints.
* [ ] Pydantic `BaseModel` usage is strict:

  * Immutability: `allow_mutation = False` for all models requiring it.
  * All business logic enforced via model validators, not in downstream logic.
  * Use structural pattern matching (`match`) for enums and unions instead of `if/else`.
* [ ] All type annotations are compatible with `mypy --strict` and pass static checks.

---

### **Architectural Fidelity & Anti-Vibecoding Rules**

* [ ] Never never improvise, overfit, or introduce speculative logic:
  * All logic must be **fully traceable** to a requirement, contract, or explicit pattern.
  * No untyped, “just works” helper code—every helper or extension must be directly referenced in PRD/spec.
* [ ] **No prompt hacking:** All deterministic business logic belongs in code, not LLM prompts.
* [ ] No silent mutations—always use `.copy(update=...)` for immutable Pydantic updates, never direct assignment or mutation.
* [ ] All branching logic must be **exhaustive** (e.g., wildcard `_` case in every `match` statement).
* [ ] No bare exceptions—catch specific exceptions, use `ExceptionGroup` for parallel flows.

---

### **Test Coverage & CI**

* [ ] Every new function or model has corresponding **unit tests**:

  * Test all structural branches, including `match…case` and error cases.
  * Test both normal and edge/failure paths.
  * Validate enforcement of immutability and error handling.
* [ ] Static analysis must pass (`mypy --strict`, `ruff`, `black`).
* [ ] Docker build/test passes in CI (`docker build .`, `pytest`, `mypy`, `ruff`, `black`).
* [ ] No skipped or commented-out tests allowed.

---

### **Observability & Error Handling**

* [ ] Use `ExceptionGroup` and `except*` for parallel/concurrent error handling.
* [ ] All custom exceptions include `.add_note(...)` for traceability and easier debugging.
* [ ] Structured logging (`structlog`, JSON output) is present at entry/exit/error points of critical code.

---

### **Reusability, Maintainability, and Scalability**

* [ ] Functions and classes are designed for reuse (no hard-coded values, no context leaks).
* [ ] All logic is modular—no monolithic files or “God classes.”
* [ ] Models, validators, and contracts are versioned and documented for traceability.
* [ ] All configs are TOML (use `tomllib`), never ad hoc constants or inline configs.
* [ ] No copy-paste patterns—if similar logic is repeated, refactor into a utility or base class.

---

### **Enterprise & Compliance Readiness**

* [ ] Session/context isolation is preserved—no cross-session state mutation.
* [ ] Security controls: no hard-coded secrets, keys, or tokens.
* [ ] All endpoints and core flows include input validation, error reporting, and audit trails.
* [ ] Compliance with SOC2/GDPR is considered (PII detection, logging).

---

### **Developer Warnings**

* ❌ Do not “fill in the blanks” or “guess” requirements—when in doubt, ask.
* ❌ Do not default to legacy patterns (e.g., `if…elif` instead of `match…case`, or `Optional` instead of `| None`).
* ❌ Do not mutate state in-place or use hacks to bypass immutability.
* ❌ Do not put business logic or branching in prompts—always code in Python.
* ❌ Do not add wrappers when refactoring core logic is needed.

---

### **Definition of Done**

* [ ] All checkboxes above are satisfied—**no partial/incomplete PRs allowed**.
* [ ] Code is “explainable” line by line, with no magic or undocumented behaviors.
* [ ] Every contract, model, or node introduced matches the architectural contract in the PRD.
* [ ] All test coverage and static analysis requirements are met.
* [ ] No deprecated code, legacy logic, or hidden state remains.

---

### **Example Modern Python Replacements**

| Outdated Pattern         | Modern Replacement (2025+)     |        |
| ------------------------ | ------------------------------ | ------ |
| `if…elif…else` for enums | `match…case…_`                 |        |
| `Optional[X]`            | \`X                            | None\` |
| `import tomli`           | `import tomllib`               |        |
| `try/except Exception:`  | `try/except* (ErrorGroup)`     |        |
| Direct mutation          | `.copy(update={...})`          |        |
| Manual config parse      | `tomllib.loads`/`tomllib.load` |        |

---

### **Example Tests**

* `match…case` branch:

  ```python
  def state_phase(phase: WorkflowPhase) -> str:
      match phase:
          case WorkflowPhase.BATCH_DISCOVERY: return "discovery"
          case WorkflowPhase.STRATEGY_ANALYSIS: return "analysis"
          case _: return "other"

  def test_state_phase():
      assert state_phase(WorkflowPhase.BATCH_DISCOVERY) == "discovery"
  ```

* `ExceptionGroup`:

  ```python
  import asyncio

  async def fail(): raise ValueError()
  async def runner(): await asyncio.gather(fail())

  def test_exception_group():
      try:
          asyncio.run(runner())
      except ExceptionGroup as eg:
          assert any(isinstance(e, ValueError) for e in eg.exceptions)
  ```

* Immutability:

  ```python
  model = MyModel(x=1)
  with pytest.raises(TypeError):
      model.x = 2
  ```

---

### **Verification Checklist**

* [ ] Outdated patterns/functions deleted.
* [ ] All core logic refactored into named modules.
* [ ] Tests pass for all edge and error conditions.
* [ ] No legacy, residual, or deprecated code remains.
* [ ] PR is reviewable, testable, scalable, and aligned with the PRD.
* [ ] Changelog is updated with a summary of latest changes.
* [ ] .Temp folder is empty. All valuable files from /.temp moved to appropriate locations. Any files starting with `temp_*` or `*_summary*`.
* [ ] Relevant architecture documents have been updated to reflect changes.

---

**Summary:**
This checklist **helps eliminate “vibecoding,” enforces architectural fidelity, and produces code that is modern, scalable, fully testable, and ready for enterprise deployment and review.**

Always reference this list before submitting any PR for review—no step may be skipped or assumed.

