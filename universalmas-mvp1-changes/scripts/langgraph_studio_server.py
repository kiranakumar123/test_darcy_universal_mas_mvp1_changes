"""
LangGraph Studio Compatible Server
==================================
A FastAPI server that provides LangGraph Studio-compatible endpoints.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import our existing workflow - we'll initialize it later to avoid import errors
workflow_graph = None

app = FastAPI(
    title="LangGraph Studio Server",
    description="LangGraph Studio compatible server for Universal Multi-Agent System",
    version="1.0.0",
)

# Add CORS middleware for Studio access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize the workflow graph lazily
def get_workflow_graph():
    global workflow_graph
    if workflow_graph is None:
        try:
            from src.universal_framework.workflow.studio_graph import (
                create_workflow_graph,
            )

            workflow_graph = create_workflow_graph()
        except Exception as e:
            print(f"Warning: Could not load workflow graph: {e}")
            workflow_graph = "mock"
    return workflow_graph


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LangGraph Studio Server", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server_type": "langgraph_studio",
        "graph_available": True,
    }


@app.get("/assistants")
async def get_assistants():
    """Get available assistants for LangGraph Studio"""
    return [
        {
            "assistant_id": "universal_workflow",
            "name": "Universal Multi-Agent Workflow",
            "description": "Universal framework for multi-agent workflows with conditional routing",
            "graph_id": "universal_workflow",
            "created_at": "2025-07-24T00:00:00Z",
            "updated_at": datetime.now().isoformat(),
            "metadata": {
                "framework": "Universal Multi-Agent System",
                "conditional_routing": True,
                "context_analysis": True,
            },
        }
    ]


@app.get("/assistants/{assistant_id}")
async def get_assistant(assistant_id: str):
    """Get specific assistant details"""
    if assistant_id != "universal_workflow":
        raise HTTPException(status_code=404, detail="Assistant not found")

    return {
        "assistant_id": "universal_workflow",
        "name": "Universal Multi-Agent Workflow",
        "description": "Universal framework for multi-agent workflows with conditional routing",
        "graph_id": "universal_workflow",
        "created_at": "2025-07-24T00:00:00Z",
        "updated_at": datetime.now().isoformat(),
        "config": {
            "configurable": {},
        },
        "metadata": {
            "framework": "Universal Multi-Agent System",
            "conditional_routing": True,
            "context_analysis": True,
            "agents": [
                "intent_classifier",
                "requirements_agent",
                "strategy_generator",
                "email_agent",
                "confirmation_agent",
            ],
        },
    }


@app.get("/threads")
async def get_threads():
    """Get conversation threads"""
    return []


@app.post("/threads")
async def create_thread():
    """Create a new conversation thread"""
    thread_id = str(uuid.uuid4())
    return {
        "thread_id": thread_id,
        "created_at": datetime.now().isoformat(),
        "metadata": {},
    }


@app.get("/threads/{thread_id}")
async def get_thread(thread_id: str):
    """Get specific thread"""
    return {
        "thread_id": thread_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "metadata": {},
    }


@app.post("/runs")
async def create_run(request: dict[str, Any]):
    """Create a new workflow run"""
    run_id = str(uuid.uuid4())
    thread_id = request.get("thread_id")
    assistant_id = request.get("assistant_id", "universal_workflow")
    input_data = request.get("input", {})

    return {
        "run_id": run_id,
        "thread_id": thread_id,
        "assistant_id": assistant_id,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "input": input_data,
    }


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get run status"""
    return {
        "run_id": run_id,
        "status": "completed",
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
    }


@app.get("/runs/{run_id}/stream")
async def stream_run(run_id: str):
    """Stream run events"""
    return {"message": "Streaming not implemented yet"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=2024)
