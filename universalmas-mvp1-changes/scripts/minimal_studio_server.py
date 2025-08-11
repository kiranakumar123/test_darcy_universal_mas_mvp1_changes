"""
Minimal LangGraph Studio Server
===============================
A working FastAPI server for LangGraph Studio.
"""

import uuid
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LangGraph Studio Server", version="1.0.0")

# Add CORS for Studio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "LangGraph Studio Server Running", "status": "healthy"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server_type": "langgraph_studio",
    }


@app.get("/assistants")
async def get_assistants():
    """Required endpoint for LangGraph Studio"""
    return [
        {
            "assistant_id": "universal_workflow",
            "name": "Universal Multi-Agent System",
            "description": "Email workflow with conditional routing",
            "graph_id": "universal_workflow",
            "created_at": "2025-07-24T00:00:00Z",
            "updated_at": datetime.now().isoformat(),
            "config": {"configurable": {}},
            "metadata": {"framework": "Universal Multi-Agent System"},
        }
    ]


@app.get("/assistants/{assistant_id}")
async def get_assistant(assistant_id: str):
    if assistant_id != "universal_workflow":
        raise HTTPException(status_code=404, detail="Assistant not found")

    return {
        "assistant_id": "universal_workflow",
        "name": "Universal Multi-Agent System",
        "description": "Email workflow with conditional routing",
        "graph_id": "universal_workflow",
        "created_at": "2025-07-24T00:00:00Z",
        "updated_at": datetime.now().isoformat(),
        "config": {"configurable": {}},
        "metadata": {"framework": "Universal Multi-Agent System"},
    }


@app.get("/threads")
async def get_threads():
    return []


@app.post("/threads")
async def create_thread():
    return {
        "thread_id": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
        "metadata": {},
    }


if __name__ == "__main__":
    print("🚀 Starting LangGraph Studio Server on http://localhost:2024")
    print(
        "📊 Studio URL: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024"
    )
    uvicorn.run(app, host="0.0.0.0", port=2024, log_level="info")
