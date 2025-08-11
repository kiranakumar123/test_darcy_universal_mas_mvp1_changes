# LangGraph Documentation Index

This directory contains all documentation related to LangGraph Studio integration with the Universal Multi-Agent System Framework.

## 📁 Directory Contents

### 📋 **Setup and Configuration**
- **[`setup_guide.md`](setup_guide.md)** - Complete installation and configuration instructions
- **[`usage_guide.md`](usage_guide.md)** - Step-by-step guide for using LangGraph Studio

### 🎨 **Visual Diagrams** 
- **[`universal_workflow.mmd`](universal_workflow.mmd)** - Mermaid diagram of the 6-phase workflow
- **[`README.md`](README.md)** - Architecture documentation and diagram viewing instructions

## 🚀 Quick Start

### 1. **Setup LangGraph Studio**
Follow the [`setup_guide.md`](setup_guide.md) to install all requirements:
- ✅ Node.js and LangGraph CLI
- ✅ Docker Desktop (optional)
- ✅ API Keys configuration

### 2. **Launch Studio**
```powershell
cd "c:\Users\darcy\OneDrive\Documents\GitHub\universalmas"
langgraph dev
```

### 3. **Access Studio UI**
Open: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

### 4. **Learn the Interface**
Read [`usage_guide.md`](usage_guide.md) for detailed Studio features and workflow testing.

## 🎯 Key Features

### **✅ Working Features**
- **🎨 Visual Workflow Graph**: Interactive 6-phase Universal Framework visualization
- **🧪 Testing Interface**: Run workflows with custom inputs
- **📊 State Inspection**: Monitor workflow state at each phase
- **⚡ Hot Reload**: Automatic updates when code changes
- **📈 Performance Metrics**: Execution time and bottleneck analysis

### **🔧 Development Tools**
- **Breakpoint Debugging**: Pause execution at specific nodes
- **Variable Inspector**: Examine state variables in detail
- **Error Visualization**: See exactly where workflows fail
- **Real-time Monitoring**: Watch message flow between agents

## 📊 Workflow Visualization

The Universal Framework implements a 6-phase workflow:

```
🚀 Initialization → 🔍 Discovery → 📊 Analysis → 🎨 Generation → ✅ Review → 📦 Delivery
```

### **Phase Details**
1. **🚀 Initialization**: Session setup and framework preparation
2. **🔍 Discovery**: Requirements gathering and context analysis  
3. **📊 Analysis**: Option evaluation and feasibility assessment
4. **🎨 Generation**: Content creation and solution development
5. **✅ Review**: Quality validation and compliance verification
6. **📦 Delivery**: Final packaging and distribution

## 🛠️ Technical Integration

### **LangGraph Configuration**
- **Graph Definition**: [`studio_graph.py`](../../src/universal_framework/workflow/studio_graph.py)
- **Configuration**: [`langgraph.json`](../../langgraph.json)
- **Environment**: [`.env`](../../.env)

### **Framework Compatibility**
- **State Model**: Uses `UniversalWorkflowState` 
- **Agent Integration**: Supports all Universal Framework agents
- **Enterprise Features**: Conditional imports and safe mode
- **Circuit Breakers**: Protection against infinite loops

## 📚 Additional Resources

### **External Links**
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **LangSmith Studio**: https://smith.langchain.com/studio/
- **Mermaid Live Editor**: https://mermaid.live

### **Project Scripts**
- **Installation**: [`scripts/langgraph/install_studio.py`](../../scripts/langgraph/install_studio.py)
- **Launch**: [`scripts/langgraph/launch_studio.py`](../../scripts/langgraph/launch_studio.py)
- **Visualization**: [`scripts/langgraph/visualize_workflow.py`](../../scripts/langgraph/visualize_workflow.py)

## 🆘 Support

### **Common Issues**
- **Studio Won't Load**: Check [`usage_guide.md#troubleshooting`](usage_guide.md#troubleshooting)
- **Import Errors**: Verify `pip install -e .` was run
- **Docker Issues**: See [`setup_guide.md#troubleshooting`](setup_guide.md#troubleshooting)

### **Getting Help**
1. Check the troubleshooting sections in the guides
2. Verify all prerequisites are installed
3. Ensure LangGraph server is running on port 2024
4. Test with the sample workflow inputs

---

**🎉 The Universal Multi-Agent System Framework is now fully integrated with LangGraph Studio for visual development and debugging!**

*Last updated: July 23, 2025*
