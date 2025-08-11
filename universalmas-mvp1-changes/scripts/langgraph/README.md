# LangGraph Scripts

This directory contains scripts for working with LangGraph Studio and workflow visualization in the Universal Multi-Agent System Framework.

## Scripts

### 🔧 `install_studio.py`
**Complete LangGraph Studio installation and setup**

Automates the entire setup process for LangGraph Studio integration.

```bash
# Check prerequisites only
python install_studio.py --check-only

# Full installation with configuration
python install_studio.py

# Include Docker installation guidance
python install_studio.py --install-docker
```

**Features:**
- ✅ Verifies all prerequisites (Python 3.11+, Node.js 18+, Docker, API keys)
- 📦 Installs LangGraph CLI automatically via pip
- ⚙️ Creates `langgraph.json` configuration file
- 📝 Generates `.env` template with required variables
- 🔍 Provides detailed status reports and troubleshooting guidance

### 🚀 `launch_studio.py`
**Convenient LangGraph Studio launcher with dependency checking**

Launches LangGraph Studio with proper configuration and environment validation.

```bash
# Launch with full dependency validation
python launch_studio.py

# Launch on custom port
python launch_studio.py --port 8124

# Check dependencies without launching
python launch_studio.py --check-deps

# Force launch (skip dependency validation)
python launch_studio.py --force
```

**Features:**
- 🔍 Pre-flight dependency checks (Docker, CLI, API keys, config)
- 🌐 Automatic browser opening to Studio UI
- 📡 Real-time output streaming from Studio process
- ⚙️ Custom port configuration
- 🛠️ Comprehensive error reporting and troubleshooting

### 🎯 `visualize_workflow.py`
**Generate workflow visualizations without Docker dependency**

Creates multiple visualization formats for the Universal Framework workflow.

```bash
# Generate all visualization formats
python visualize_workflow.py

# Generate only Mermaid diagram
python visualize_workflow.py --format mermaid

# Custom output directory
python visualize_workflow.py --output-dir ./my_visualizations

# Generate specific format
python visualize_workflow.py --format ascii
```

**Formats:**
- **Mermaid**: Interactive diagrams for mermaid.live and VS Code
- **ASCII**: Terminal-friendly text representations
- **Analysis**: Detailed workflow structure documentation
- **Component Inventory**: Framework components scan

## Quick Start

### 1. First-Time Setup
```bash
# Navigate to scripts directory
cd scripts/langgraph

# Install and configure everything
python install_studio.py

# Verify all dependencies
python install_studio.py --check-only
```

### 2. Generate Visualizations (No Docker Required)
```bash
# Create workflow diagrams
python visualize_workflow.py

# View Mermaid diagram at: https://mermaid.live
# Find generated files in: ./visualizations/
```

### 3. Launch Studio UI (Requires Docker)
```bash
# Start Studio with dependency checks
python launch_studio.py

# Access Studio at: http://localhost:8123
```

## Prerequisites

### Required Software
- **Python 3.11+** ✅ (Universal Framework requirement)
- **Node.js 18+** ✅ (For Studio UI frontend components)
- **Docker Desktop** ⏳ (For full Studio experience)

### Required API Keys
- **OpenAI API Key** ✅ (For LLM operations)
- **LangSmith API Key** ✅ (For tracing and observability)

### Environment Setup
```powershell
# Set API keys in PowerShell session
$env:OPENAI_API_KEY="your_openai_api_key_here"
$env:LANGSMITH_API_KEY="your_langsmith_api_key_here"
```

## Configuration

### Generated Files
Scripts create these configuration files in the project root:

- **`langgraph.json`** - Studio configuration
- **`.env`** - Environment variables template

### Output Locations
- **Visualizations**: `./visualizations/` (configurable)
- **Mermaid Diagrams**: `../../docs/langgraph/`
- **Documentation**: `../../docs/langgraph/`

## Integration Points

### Framework Integration
Scripts integrate with the Universal Framework through:

```python
# Entry point for Studio visualization
"./src/universal_framework/workflow/builder.py:create_workflow"
```

### State Compatibility
All visualizations work with `UniversalWorkflowState`:

```python
class UniversalWorkflowState(BaseModel):
    messages: List[BaseMessage]
    current_phase: str
    session_id: str
    metadata: Dict[str, Any]
```

## Troubleshooting

### Common Issues

**Docker not available**
```bash
# Use visualization without Docker
python visualize_workflow.py
```

**Port conflicts**
```bash
# Use different port
python launch_studio.py --port 8124
```

**API keys missing**
```bash
# Check current settings
python install_studio.py --check-only
```

### Debug Commands
```bash
# Comprehensive dependency check
python install_studio.py --check-only

# Test workflow compilation
python -c "from src.universal_framework.workflow.builder import create_workflow; print('✅ OK')"
```

## Related Documentation

- **LangGraph Documentation Hub**: `../../docs/langgraph/`
- **Setup Guide**: `../../docs/langgraph/setup_guide.md`
- **Usage Guide**: `../../docs/langgraph/usage_guide.md`
- **Architecture Diagrams**: `../../docs/langgraph/universal_workflow.mmd`
- **Framework Documentation**: `../../docs/AGENTS.md`

---

*Scripts support both development (memory-only) and production (Redis) configurations.*
