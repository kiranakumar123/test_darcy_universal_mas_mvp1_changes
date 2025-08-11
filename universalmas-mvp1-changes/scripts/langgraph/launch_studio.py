#!/usr/bin/env python3
"""
LangGraph Studio Launcher

Convenient script for launching LangGraph Studio with proper configuration
and environment setup for the Universal Framework.

Usage:
    python launch_studio.py [OPTIONS]

Options:
    --port PORT        Studio UI port (default: 8123)
    --check-deps       Check dependencies before launch
    --force           Launch even if dependencies missing
    --config FILE     Custom langgraph.json config file
"""

import argparse
import json
import os
import subprocess
import time
import webbrowser
from pathlib import Path


def check_docker_running() -> tuple[bool, str]:
    """Check if Docker is installed and running"""
    try:
        result = subprocess.run(
            ["docker", "ps"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, "Docker is running"
        else:
            return False, "Docker installed but not running"
    except FileNotFoundError:
        return False, "Docker not installed"
    except subprocess.TimeoutExpired:
        return False, "Docker command timed out"
    except Exception as e:
        return False, f"Docker check failed: {e}"


def check_langgraph_cli() -> tuple[bool, str]:
    """Check if LangGraph CLI is available"""
    try:
        result = subprocess.run(
            ["langgraph", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, f"LangGraph CLI {result.stdout.strip()}"
        else:
            return False, "LangGraph CLI not responding"
    except FileNotFoundError:
        return False, "LangGraph CLI not installed"
    except Exception as e:
        return False, f"LangGraph CLI check failed: {e}"


def check_api_keys() -> tuple[bool, str]:
    """Check if required API keys are set"""
    openai_key = os.getenv("OPENAI_API_KEY")
    langsmith_key = os.getenv("LANGSMITH_API_KEY")

    issues = []
    if not openai_key:
        issues.append("OPENAI_API_KEY not set")
    if not langsmith_key:
        issues.append("LANGSMITH_API_KEY not set")

    if issues:
        return False, "; ".join(issues)
    else:
        return True, "API keys configured"


def check_config_file(config_path: Path) -> tuple[bool, str]:
    """Check if langgraph.json exists and is valid"""
    if not config_path.exists():
        return False, f"Config file not found: {config_path}"

    try:
        with open(config_path) as f:
            config = json.load(f)

        # Check required fields
        required_fields = ["dependencies", "graphs"]
        missing = [field for field in required_fields if field not in config]

        if missing:
            return False, f"Missing required fields: {missing}"

        return True, "Configuration valid"

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Config check failed: {e}"


def run_dependency_check(config_path: Path) -> bool:
    """Run comprehensive dependency check"""
    print("🔍 Checking LangGraph Studio Dependencies")
    print("=" * 45)

    checks = [
        ("Docker", check_docker_running()),
        ("LangGraph CLI", check_langgraph_cli()),
        ("API Keys", check_api_keys()),
        ("Configuration", check_config_file(config_path)),
    ]

    all_good = True
    for name, (success, message) in checks:
        status = "✅" if success else "❌"
        print(f"{status} {name}: {message}")
        if not success:
            all_good = False

    print("=" * 45)
    return all_good


def launch_studio(port: int, config_path: Path, force: bool = False) -> bool:
    """Launch LangGraph Studio"""

    # Check dependencies unless forced
    if not force:
        if not run_dependency_check(config_path):
            print("\n❌ Dependencies not met. Use --force to launch anyway.")
            print("\n💡 Quick fixes:")
            print("• Start Docker Desktop")
            print("• Set API keys: $env:OPENAI_API_KEY='your_key'")
            print("• Install CLI: pip install langgraph-cli")
            return False

    print(f"\n🚀 Launching LangGraph Studio on port {port}")
    print("-" * 40)

    # Change to project directory
    project_root = config_path.parent
    os.chdir(project_root)

    try:
        # Launch Studio
        cmd = ["langgraph", "up", "--debugger-port", str(port)]

        print(f"📡 Running: {' '.join(cmd)}")
        print(f"📁 Working directory: {project_root}")
        print(f"🔧 Config file: {config_path}")

        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Wait a moment for startup
        time.sleep(3)

        if process.poll() is None:
            # Process is running
            studio_url = f"http://localhost:{port}"
            print("✅ LangGraph Studio starting...")
            print(f"🌐 URL: {studio_url}")

            # Try to open browser
            try:
                webbrowser.open(studio_url)
                print("🌏 Opened in default browser")
            except:
                print("🔗 Open manually in browser")

            print("\n💡 Studio Features:")
            print("• 🎯 Visual workflow graphs")
            print("• 🔍 Step-by-step debugging")
            print("• 📊 State inspection")
            print("• 🎮 Interactive testing")
            print("• 📈 Performance metrics")

            print("\n⏹️  To stop: Ctrl+C or 'langgraph down'")

            # Stream output
            try:
                for line in process.stdout:
                    print(line.rstrip())
            except KeyboardInterrupt:
                print("\n⏹️  Stopping LangGraph Studio...")
                process.terminate()
                return True
        else:
            # Process failed to start
            print("❌ Failed to start LangGraph Studio")
            if process.stdout:
                output = process.stdout.read()
                print(f"Error output: {output}")
            return False

    except FileNotFoundError:
        print("❌ LangGraph CLI not found. Install with:")
        print("   pip install langgraph-cli")
        return False
    except Exception as e:
        print(f"❌ Launch failed: {e}")
        return False


def main():
    """Main launcher function"""
    parser = argparse.ArgumentParser(description="LangGraph Studio Launcher")
    parser.add_argument(
        "--port", type=int, default=8123, help="Studio UI port (default: 8123)"
    )
    parser.add_argument(
        "--check-deps", action="store_true", help="Check dependencies and exit"
    )
    parser.add_argument(
        "--force", action="store_true", help="Launch even if dependencies missing"
    )
    parser.add_argument("--config", help="Custom langgraph.json config file")

    args = parser.parse_args()

    # Find project root and config file
    if args.config:
        config_path = Path(args.config)
    else:
        # Default to project root
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "langgraph.json"

    print("🚀 LangGraph Studio Launcher")
    print(f"📁 Config: {config_path}")
    print(f"🌐 Port: {args.port}")
    print("=" * 50)

    if args.check_deps:
        success = run_dependency_check(config_path)
        if success:
            print("\n✅ All dependencies ready!")
            print(f"🚀 Launch with: python {__file__} --port {args.port}")
        else:
            print("\n❌ Fix dependencies above, then try again.")
        return

    # Launch Studio
    success = launch_studio(args.port, config_path, args.force)

    if success:
        print("\n👋 LangGraph Studio session ended.")
    else:
        print("\n❌ Failed to launch LangGraph Studio.")
        print("\n🔧 Troubleshooting:")
        print("• Check Docker is running")
        print("• Verify API keys are set")
        print("• Run with --check-deps for details")


if __name__ == "__main__":
    main()
