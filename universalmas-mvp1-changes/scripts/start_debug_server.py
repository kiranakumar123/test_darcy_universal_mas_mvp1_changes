#!/usr/bin/env python3
"""
Simple server runner to test our debugging functionality
"""
import os
import sys
from pathlib import Path

# Set working directory
os.chdir(Path(__file__).parent)

# Set environment variables for debugging
os.environ["PYTHONPATH"] = str(Path.cwd() / "src")
os.environ["LOG_LEVEL"] = "DEBUG"

# Check if uvicorn is available
try:
    import uvicorn

    print("Starting development server with debugging enabled...")

    # Import and run the app
    sys.path.insert(0, str(Path.cwd() / "src"))

    try:
        from universal_framework.api.app_factory import create_app

        app = create_app()

        print("Server starting on http://localhost:8000")
        print("Debug logging is enabled - you should see detailed logs for:")
        print("- Session state retrieval")
        print("- Intent classification flow")
        print("- Response size monitoring")
        print("\nTry these test requests:")
        print("1. POST /api/v1/workflow/execute with a help request")
        print("2. Include session_config in the request to test phase-aware help")

        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")

    except ImportError as e:
        print(f"Import error: {e}")
        print("Dependencies may need to be resolved")

except ImportError:
    print("uvicorn not found. Try: pip install uvicorn")
