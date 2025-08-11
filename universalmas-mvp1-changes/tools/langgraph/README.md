# LangGraph Tools

This directory contains tools and scripts for working with LangGraph Studio and workflow visualization in the Universal Multi-Agent System Framework.

## Scripts Overview

### 🔧 `install_studio.py`
**Complete LangGraph Studio installation and setup**

- Checks all prerequisites (Python, Node.js, Docker, API keys)
- Installs LangGraph CLI automatically
- Creates configuration files (`langgraph.json`, `.env` template)
- Provides detailed status reports and troubleshooting

```bash
# Check prerequisites only
python install_studio.py --check-only

# Full installation
python install_studio.py

# Include Docker installation attempt
python install_studio.py --install-docker
```

### 🎯 `visualize_workflow.py`
**Generate workflow visualizations without Docker**

- Creates Mermaid diagrams for interactive viewing
- Generates ASCII representations for terminal viewing
- Analyzes workflow structure and components
- Scans actual framework component inventory

```bash
# Generate all visualization formats
python visualize_workflow.py

# Generate only Mermaid diagram
python visualize_workflow.py --format mermaid

# Custom output directory
python visualize_workflow.py --output-dir ./my_visualizations
```

### 🚀 `launch_studio.py`
**Convenient LangGraph Studio launcher**

- Performs dependency checks before launch
- Launches Studio with proper configuration
- Opens browser automatically
- Provides real-time output streaming

```bash
# Launch with dependency check
python launch_studio.py

# Launch on custom port
python launch_studio.py --port 8124

# Check dependencies only
python launch_studio.py --check-deps

# Force launch (skip dependency check)
python launch_studio.py --force
```

## Quick Start

### 1. First-Time Setup
```bash
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
```

### 3. Launch Studio UI (Requires Docker)
```bash
# Start Studio with checks
python launch_studio.py

# Access at: http://localhost:8123
```

## Configuration Files

### `langgraph.json`
Studio configuration automatically created by `install_studio.py`:

```json
{
  "dependencies": ["./src"],
  "graphs": {
    "universal_workflow": "./src/universal_framework/workflow/builder.py:create_workflow"
  },
  "env": ".env",
  "python_version": "3.11",
  "pip_config_file": "requirements.txt",
  "dockerfile": "Dockerfile.dev"
}
```

### `.env` Template
Environment variables template:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# LangSmith Configuration
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=universal-framework-dev

# Framework Configuration
SAFE_MODE=true
ENTERPRISE_FEATURES=false
```

## Prerequisites

### Required Software
- **Python 3.11+** ✅ (Framework requirement)
- **Node.js 18+** ✅ (For Studio UI frontend)
- **Docker Desktop** ⏳ (For full Studio experience)

### Required API Keys
- **OpenAI API Key** ✅ (For LLM operations)
- **LangSmith API Key** ✅ (For tracing and observability)

## Output Files

### Visualization Output
When running `visualize_workflow.py`, files are generated in `./visualizations/`:

- `universal_workflow.mmd` - Mermaid diagram code
- `workflow_analysis.md` - Detailed structure analysis
- `framework_components.md` - Component inventory

### Studio Configuration
Configuration files in project root:

- `langgraph.json` - Studio configuration
- `.env` - Environment variables (template)

## Troubleshooting

### Common Issues

**"Docker not installed"**
```bash
# Install Docker Desktop
# Download from: https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe
# Or use: winget install Docker.DockerDesktop
```

**"LangGraph CLI not found"**
```bash
pip install langgraph-cli
```

**"API keys not set"**
```powershell
$env:OPENAI_API_KEY="your_key_here"
$env:LANGSMITH_API_KEY="your_key_here"
```

**"Port already in use"**
```bash
python launch_studio.py --port 8124
```

### Debug Commands

```bash
# Check all prerequisites
python install_studio.py --check-only

# Test workflow compilation
python -c "from src.universal_framework.workflow.builder import create_workflow; print('✅ Workflow builds')"

# Verify API keys
echo $env:OPENAI_API_KEY
echo $env:LANGSMITH_API_KEY
```

## Integration with Framework

### Workflow Builder
Studio integrates with the framework's workflow builder:

```python
# src/universal_framework/workflow/builder.py
def create_workflow() -> CompiledGraph:
    """Entry point called by LangGraph Studio"""
    return workflow_builder.build()
```

### State Compatibility
Studio visualizes `UniversalWorkflowState` transitions:

```python
class UniversalWorkflowState(BaseModel):
    messages: List[BaseMessage]
    current_phase: str
    session_id: str
    metadata: Dict[str, Any]
```

## Development Workflow

### Visual Debugging Process
1. **Modify workflow code** in `src/universal_framework/`
2. **Launch Studio** with `python launch_studio.py`
3. **Test workflows** in Studio playground
4. **Inspect state** at each step
5. **Debug issues** using visual flow
6. **Optimize performance** based on metrics

### Alternative Workflows
- **No Docker**: Use `visualize_workflow.py` for static diagrams
- **Development**: Use memory checkpointing (current setup)
- **Production**: Switch to Redis checkpointing for persistence

---

For complete setup instructions, see `../docs/langgraph_studio_setup.md`.
