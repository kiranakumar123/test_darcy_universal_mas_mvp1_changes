#!/usr/bin/env python3
"""
Docker-Free LangGraph Studio Alternative
========================================

Launches a local development server for workflow visualization without Docker.
Uses LangGraph's built-in development server capabilities.
"""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def setup_environment():
    """Set up the environment for LangGraph development server"""
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    # Add project to Python path
    if str(project_root / "src") not in sys.path:
        sys.path.insert(0, str(project_root / "src"))

    print(f"📁 Working directory: {project_root}")
    return project_root


def check_prerequisites():
    """Check if we have the minimum requirements"""
    print("🔍 Checking prerequisites...")

    # Check Python
    print(f"✅ Python: {sys.version.split()[0]}")

    # Check LangGraph CLI
    try:
        result = subprocess.run(
            ["langgraph", "--version"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ LangGraph CLI: {result.stdout.strip()}")
        else:
            print("❌ LangGraph CLI not found")
            return False
    except FileNotFoundError:
        print("❌ LangGraph CLI not installed")
        return False

    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    langsmith_key = os.getenv("LANGSMITH_API_KEY")

    if openai_key:
        print(f"✅ OpenAI API Key: {openai_key[:8]}...")
    else:
        print("⚠️ OpenAI API Key not set")

    if langsmith_key:
        print(f"✅ LangSmith API Key: {langsmith_key[:8]}...")
    else:
        print("⚠️ LangSmith API Key not set")

    return True


def test_workflow_import():
    """Test if our workflow can be imported"""
    print("🧪 Testing workflow import...")

    try:
        from src.universal_framework.workflow.graph import create_workflow_graph

        workflow = create_workflow_graph()
        print("✅ Workflow import successful")
        return True
    except Exception as e:
        print(f"❌ Workflow import failed: {e}")
        return False


def launch_dev_server():
    """Launch LangGraph development server"""
    print("\n🚀 Launching LangGraph Development Server...")
    print("=" * 50)

    try:
        # Try LangGraph development server without Docker
        cmd = ["langgraph", "dev", "--debugger-port", "8123", "--no-docker"]

        print(f"📡 Running: {' '.join(cmd)}")

        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Give it a moment to start
        time.sleep(3)

        if process.poll() is None:
            print("✅ Development server starting...")

            # Try to open browser
            studio_url = "http://localhost:8123"
            print(f"🌐 Studio URL: {studio_url}")

            try:
                webbrowser.open(studio_url)
                print("🌏 Opened in default browser")
            except:
                print("🔗 Please open manually in browser")

            print("\n💡 Development Server Features:")
            print("• 📊 Workflow visualization")
            print("• 🔍 Real-time debugging")
            print("• 📝 Interactive testing")
            print("• 🎯 No Docker required!")

            print("\n⏹️ To stop: Ctrl+C")

            # Stream output
            try:
                for line in process.stdout:
                    print(line.rstrip())
            except KeyboardInterrupt:
                print("\n⏹️ Stopping development server...")
                process.terminate()
                return True
        else:
            print("❌ Failed to start development server")
            return False

    except Exception as e:
        print(f"❌ Launch failed: {e}")
        return False


def fallback_visualization():
    """Fallback to static visualization if dev server fails"""
    print("\n🎯 Fallback: Generating static visualization...")

    try:
        # Use our visualization script
        cmd = ["python", "scripts/langgraph/visualize_workflow.py"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Static visualization generated!")
            print(result.stdout)
            return True
        else:
            print(f"❌ Visualization failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Fallback visualization failed: {e}")
        return False


def main():
    """Main function"""
    print("🚀 Docker-Free LangGraph Studio")
    print("=" * 40)

    # Setup
    project_root = setup_environment()

    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met")
        return

    # Test workflow
    if not test_workflow_import():
        print("\n❌ Workflow issues detected")
        print("💡 Try: python scripts/langgraph/visualize_workflow.py")
        return

    print("\n✅ All checks passed!")

    # Try development server
    success = launch_dev_server()

    if not success:
        print("\n🔄 Development server failed, trying fallback...")
        fallback_visualization()


if __name__ == "__main__":
    main()
