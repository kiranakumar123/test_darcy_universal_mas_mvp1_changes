# LangGraph Studio Setup and Configuration Guide

## Overview

This document provides complete instructions for setting up and configuring LangGraph Studio for visual debugging of the Universal Multi-Agent System Framework workflows.

## What is LangGraph Studio?

LangGraph Studio is a visual development environment for LangGraph workflows that provides:
- 🎯 **Interactive Workflow Visualization** - See your agents and nodes as flowcharts
- 🔍 **Real-time Debugging** - Watch messages flow between agents step-by-step
- 📊 **State Inspection** - View `UniversalWorkflowState` at each workflow phase
- 🎮 **Interactive Testing** - Send test messages and observe execution
- 📈 **Performance Metrics** - Monitor execution times and bottlenecks
- 🐛 **Error Visualization** - Identify where workflows fail or get stuck

## Prerequisites

### Required Software
- **Windows 10/11** with PowerShell
- **Python 3.11+** (framework requirement)
- **Node.js 18+** (for Studio UI frontend)
- **Docker Desktop** (for full Studio experience)

### Required API Keys
- **OpenAI API Key** - For LLM operations
- **LangSmith API Key** - For tracing and observability

## Installation Steps

### 1. Install Node.js (✅ Completed)

```powershell
# Using Chocolatey (recommended)
choco install nodejs

# Verify installation
node --version  # Should show v24.4.1 or newer
npm --version   # Should show v11.4.2 or newer
```

### 2. Install LangGraph CLI (✅ Completed)

```powershell
# Install via pip
pip install langgraph-cli

# Verify installation
langgraph --version  # Should show 0.2.60 or newer
```

### 3. Configure API Keys (✅ Completed)

Create or update your `.env` file in the project root:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# LangSmith Configuration  
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=universal-framework-dev
```

**Set in PowerShell session:**
```powershell
$env:OPENAI_API_KEY="your_key_here"
$env:LANGSMITH_API_KEY="your_key_here"
```

### 4. Install Docker Desktop (⏳ In Progress)

**Option A: Direct Download**
1. Download from: https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe
2. Run installer and follow setup wizard
3. Restart Windows if prompted
4. Start Docker Desktop application

**Option B: Package Manager**
```powershell
# Using winget (if available)
winget install Docker.DockerDesktop

# Using Chocolatey
choco install docker-desktop
```

**Verify Docker Installation:**
```powershell
docker --version
docker ps  # Should show running containers (empty list is OK)
```

## Configuration Files

### LangGraph Studio Configuration (✅ Created)

**File: `langgraph.json`**
```json
{
  "dependencies": [
    "./src"
  ],
  "graphs": {
    "universal_workflow": "./src/universal_framework/workflow/builder.py:create_workflow"
  },
  "env": ".env",
  "python_version": "3.11",
  "pip_config_file": "requirements.txt",
  "dockerfile": "Dockerfile.dev"
}
```

This configuration:
- Points to workflow builder in `src/universal_framework/workflow/builder.py`
- Uses memory-only checkpointing (no Redis dependency)
- Loads environment variables from `.env` file
- Uses development Docker configuration

## Launching LangGraph Studio

### Method 1: Full Studio UI (Requires Docker)

```powershell
# Navigate to project directory
cd c:\Users\darcy\OneDrive\Documents\GitHub\universalmas

# Launch Studio with debugging port
langgraph up --debugger-port 8123

# Access Studio UI
# Browser will automatically open to: http://localhost:8123
```

**Studio UI Features:**
- **Graph View** - Interactive workflow visualization
- **Runs Tab** - View execution history and traces
- **Playground** - Test workflows with custom inputs
- **State Inspector** - Deep dive into state at each step

### Method 2: CLI Visualization (No Docker Required) (✅ Working)

```powershell
# Generate Mermaid diagrams
python .temp\temp_simple_visualizer.py

# View generated Mermaid code
# Copy output and paste at: https://mermaid.live
```

## Configuration Options

### Memory vs Redis Checkpointing

**Current Setup: Memory-Only (Recommended for Development)**
- ✅ No Redis installation required
- ✅ Faster startup and debugging
- ✅ No external dependencies
- ❌ State not persisted between restarts

**Production Setup: Redis Checkpointing**
```python
# In builder.py, switch to Redis when available
from langgraph.checkpoint.redis import RedisSaver
checkpointer = RedisSaver(redis_conn)
```

### Environment-Specific Configuration

**Development Mode:**
```env
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=universal-framework-dev
SAFE_MODE=true
ENTERPRISE_FEATURES=false
```

**Production Mode:**
```env
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=universal-framework-prod
SAFE_MODE=false
ENTERPRISE_FEATURES=true
```

## Troubleshooting

### Common Issues

**1. "Docker not installed" Error**
```bash
Error: Docker not installed
```
**Solution:** Complete Docker Desktop installation and ensure it's running

**2. "Port already in use" Error**
```bash
Error: Port 8123 is already in use
```
**Solution:** Use different port or kill existing process
```powershell
langgraph up --debugger-port 8124
```

**3. Import Errors in Studio**
```bash
ImportError: cannot import name 'EnvironmentConfig'
```
**Solution:** Check Python path and dependencies in `langgraph.json`

**4. API Key Not Found**
```bash
Warning: OPENAI_API_KEY not found
```
**Solution:** Verify environment variables are set
```powershell
echo $env:OPENAI_API_KEY
```

### Debug Commands

**Check Studio Status:**
```powershell
# View running processes
langgraph ps

# Check logs
langgraph logs

# Stop Studio
langgraph down
```

**Validate Configuration:**
```powershell
# Check langgraph.json syntax
python -m json.tool langgraph.json

# Test workflow compilation
python -c "from src.universal_framework.workflow.builder import create_workflow; print('✅ Workflow builds successfully')"
```

## Development Workflow

### 1. Start Studio Session

```powershell
# Launch Studio
langgraph up --debugger-port 8123

# Access in browser
start http://localhost:8123
```

### 2. Test Workflow Changes

1. **Modify workflow code** in `src/universal_framework/`
2. **Refresh Studio UI** to see updates
3. **Run test executions** in Studio playground
4. **Inspect state changes** in real-time
5. **Debug issues** using visual flow

### 3. Performance Analysis

- **Monitor execution times** for each node
- **Identify bottlenecks** in agent processing
- **Optimize slow components** based on metrics
- **Test circuit breaker behavior** under load

## Integration with Framework

### Workflow Builder Integration

The Studio integrates with our workflow builder:

```python
# src/universal_framework/workflow/builder.py
def create_workflow() -> CompiledGraph:
    """Create workflow for LangGraph Studio visualization"""
    # This function is called by Studio
    # Must return CompiledGraph for visualization
```

### State Compatibility

Studio works with our `UniversalWorkflowState`:

```python
# All state transitions are visible in Studio
class UniversalWorkflowState(BaseModel):
    messages: List[BaseMessage]
    current_phase: str
    session_id: str
    metadata: Dict[str, Any]
```

### Agent Debugging

Individual agents can be tested in isolation:

```python
# Debug specific agents in Studio playground
from universal_framework.agents.requirements_agent import RequirementsAgent
# Test with specific inputs and observe behavior
```

## Next Steps

1. **Complete Docker Installation** - For full Studio UI experience
2. **Launch Studio UI** - Visual debugging interface
3. **Test Workflow Execution** - Validate circuit breaker fixes
4. **Performance Optimization** - Use Studio metrics for tuning
5. **Production Configuration** - Switch to Redis checkpointing when ready

## References

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **LangGraph Studio Guide**: https://langchain-ai.github.io/langgraph/how-tos/debug-graphs/
- **Mermaid Live Editor**: https://mermaid.live
- **LangSmith Tracing**: https://smith.langchain.com/

---

*This documentation represents the current state of LangGraph Studio integration with the Universal Multi-Agent System Framework as of July 22, 2025.*
