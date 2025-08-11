# UNIVERSAL MULTI-AGENT SYSTEM FRAMEWORK

Enterprise-grade foundation for any multi-agent application

---

## Overview

The **Universal Multi-Agent System Framework** provides an enterprise-ready, highly-adaptable platform for building, orchestrating, and deploying multi-agent workflows in any domain.
Built on best practices from Custom GPT Builder, this framework is engineered for reliability, modularity, and scale—meeting the needs of organizations that demand robust automation, compliance, and performance.

---

## Key Features

* **Composable 33+ node workflow architecture**
* **Strict FSM state enforcement** for every workflow phase
* **MAESTRO security framework** for enterprise controls
* **Redis-based session management** for high-concurrency and reliability
* **Context-aware error handling and recovery**
* **Enterprise-grade performance standards** (<500ms target per node)
* **Audit, checkpoint, and compliance built-in**

---

## Adaptable For

* **Communications:**
  Generate emails, presentations, implementation plans, and more.
* **Document Generation Systems:**
  Automate the creation of executive summaries, detailed reports, slides, and appendices.
* **Data Analysis Workflows:**
  Analyze data, surface insights, and deliver visualizations with traceable agent logic.
* **Content Creation Pipelines:**
  Produce marketing copy, blog posts, or campaign assets in a fully-managed flow.
* **Business Process Automation:**
  Orchestrate and document multi-step procedures, compliance checks, or employee onboarding.
* **And any other multi-agent, workflow-driven use case**

---

## Architecture

* **Universal State Management:**
  The `UniversalWorkflowState` dataclass holds session data, phase tracking, context, audit, outputs, and all agent-driven modifications for each workflow.
* **Workflow Phases (FSM):**
  Each use case moves through strict, enforced stages:
  `initialization → discovery → analysis → generation → review → delivery → completion`
* **Pluggable Agent Roles:**
  Each workflow phase is powered by one or more agents (e.g., requirement analyst, data analyst, quality validator) defined in a universal registry and ready for domain specialization.
* **Edge Mapping & Routing:**
  Conditional transitions between nodes ensure robust state transitions and global command support (debug, restart, go back, help).
* **Enterprise Controls:**
  Security enforcement, audit trails, trace overlays, dynamic persona adaptation, error handling, and performance metrics are built-in for compliance and reliability.

---

## Templates & Developer Resources

A dedicated `templates/` directory contains **reference implementations and best-practice templates** for:

* Standard LangChain agents and chains
* LangGraph workflow/node patterns
* LangSmith tracing/instrumentation
* Integration adapters (Qdrant, Datadog, Kubernetes, etc.)

> **Whenever a task, user story, or component references a "template" or standard pattern, start with the matching entry from `templates/` as the canonical foundation.**
> If no template fits, consult the project architect before diverging from the established standard.

---

## Technology Stack

* **Python 3.11+**
* [LangChain](https://github.com/langchain-ai/langchain) (agent abstractions, messaging)
* [LangGraph](https://github.com/langchain-ai/langgraph) (workflow and FSM orchestration)
* [LangSmith](https://smith.langchain.com/) (tracing, observability, experiment management)
* [Redis](https://redis.io/) (multi-session state, checkpointing)
* **API-ready for:**
  * [Qdrant](https://qdrant.tech/) (vector database for RAG/memory)
  * [Datadog](https://www.datadoghq.com/) (logging, APM, monitoring)
  * [Kubernetes](https://kubernetes.io/) (container deployment and orchestration)
* **Testing:** pytest
* **Code Style:** PEP8 with [Black](https://github.com/psf/black) auto-formatting

> *Initial deployments may not include Qdrant, Datadog, or Kubernetes, but all code and adapters are ready for plug-and-play integration.*

## Code Quality Standards

This project enforces strict formatting and linting rules.

### Developer Setup

```bash
pip install -r requirements-dev.txt
pre-commit install
```

`requirements-dev.txt` now includes `psutil` for performance testing utilities.

### Manual Commands

```bash
# Format code
black .

# Lint and auto-fix issues
ruff check . --fix

# Run all pre-commit hooks
pre-commit run --all-files
```

### CI Integration

Add these commands to your CI pipeline:

```bash
black --check .
ruff check .
```
