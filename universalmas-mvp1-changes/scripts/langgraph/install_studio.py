#!/usr/bin/env python3
"""
LangGraph Studio Installation and Setup Script

Comprehensive script for installing and configuring LangGraph Studio
for visual workflow debugging of the Universal Framework.

Usage:
    python install_studio.py [--check-only] [--install-docker]

Features:
    - Verifies all prerequisites (Node.js, Python, API keys)
    - Installs LangGraph CLI if needed
    - Validates Docker installation
    - Creates Studio configuration files
    - Provides detailed setup instructions
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH"""
    return shutil.which(command) is not None


def run_command(command: str, capture_output: bool = True) -> tuple[bool, str]:
    """Run a command and return success status and output"""
    try:
        if capture_output:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0, result.stdout.strip()
        else:
            result = subprocess.run(command, shell=True, timeout=30)
            return result.returncode == 0, ""
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def check_node_js() -> tuple[bool, str]:
    """Check Node.js installation and version"""
    if not check_command_exists("node"):
        return False, "Node.js not installed"

    success, version = run_command("node --version")
    if not success:
        return False, "Failed to get Node.js version"

    # Parse version (format: v24.4.1)
    try:
        version_num = version.lstrip("v").split(".")[0]
        if int(version_num) >= 18:
            return True, f"Node.js {version} (✓ Compatible)"
        else:
            return False, f"Node.js {version} (✗ Need v18+)"
    except:
        return False, f"Invalid Node.js version format: {version}"


def check_python() -> tuple[bool, str]:
    """Check Python installation and version"""
    try:
        version = sys.version_info
        if version.major == 3 and version.minor >= 11:
            return (
                True,
                f"Python {version.major}.{version.minor}.{version.micro} (✓ Compatible)",
            )
        else:
            return (
                False,
                f"Python {version.major}.{version.minor}.{version.micro} (✗ Need 3.11+)",
            )
    except:
        return False, "Failed to get Python version"


def check_docker() -> tuple[bool, str]:
    """Check Docker installation and status"""
    if not check_command_exists("docker"):
        return False, "Docker not installed"

    # Check Docker version
    success, version = run_command("docker --version")
    if not success:
        return False, "Docker installed but not accessible"

    # Check if Docker is running
    success, _ = run_command("docker ps")
    if not success:
        return False, f"Docker installed ({version}) but not running"

    return True, f"Docker {version} (✓ Running)"


def check_langgraph_cli() -> tuple[bool, str]:
    """Check LangGraph CLI installation"""
    if not check_command_exists("langgraph"):
        return False, "LangGraph CLI not installed"

    success, version = run_command("langgraph --version")
    if not success:
        return False, "LangGraph CLI installed but not accessible"

    return True, f"LangGraph CLI {version} (✓ Installed)"


def check_api_keys() -> dict[str, tuple[bool, str]]:
    """Check required API keys"""
    keys = {
        "OpenAI": os.getenv("OPENAI_API_KEY"),
        "LangSmith": os.getenv("LANGSMITH_API_KEY"),
    }

    results = {}
    for name, key in keys.items():
        if key:
            masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
            results[name] = (True, f"{name} API Key: {masked_key} (✓ Set)")
        else:
            results[name] = (False, f"{name} API Key: Not set")

    return results


def install_langgraph_cli() -> tuple[bool, str]:
    """Install LangGraph CLI via pip"""
    print("📦 Installing LangGraph CLI...")
    success, output = run_command("pip install langgraph-cli", capture_output=False)

    if success:
        # Verify installation
        cli_success, version = check_langgraph_cli()
        if cli_success:
            return True, f"Successfully installed LangGraph CLI {version}"
        else:
            return False, "Installation completed but CLI not accessible"
    else:
        return False, f"Installation failed: {output}"


def create_langgraph_config(project_root: Path) -> tuple[bool, str]:
    """Create langgraph.json configuration file"""
    config = {
        "dependencies": ["./src"],
        "graphs": {
            "universal_workflow": "./src/universal_framework/workflow/builder.py:create_workflow"
        },
        "env": ".env",
        "python_version": "3.11",
        "pip_config_file": "requirements.txt",
        "dockerfile": "Dockerfile.dev",
    }

    config_path = project_root / "langgraph.json"

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return True, f"Created langgraph.json at {config_path}"
    except Exception as e:
        return False, f"Failed to create langgraph.json: {e}"


def create_env_template(project_root: Path) -> tuple[bool, str]:
    """Create .env template if it doesn't exist"""
    env_path = project_root / ".env"

    if env_path.exists():
        return True, f".env already exists at {env_path}"

    template = """# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# LangSmith Configuration
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=universal-framework-dev

# Framework Configuration
SAFE_MODE=true
ENTERPRISE_FEATURES=false
"""

    try:
        with open(env_path, "w") as f:
            f.write(template)
        return True, f"Created .env template at {env_path}"
    except Exception as e:
        return False, f"Failed to create .env template: {e}"


def print_status_report():
    """Print comprehensive status report"""
    print("🔍 LangGraph Studio Prerequisites Check")
    print("=" * 50)

    # Check all prerequisites
    checks = {
        "Python": check_python(),
        "Node.js": check_node_js(),
        "Docker": check_docker(),
        "LangGraph CLI": check_langgraph_cli(),
    }

    # Check API keys
    api_keys = check_api_keys()
    checks.update(api_keys)

    # Print results
    all_good = True
    for name, (success, message) in checks.items():
        status = "✅" if success else "❌"
        print(f"{status} {name}: {message}")
        if not success:
            all_good = False

    print("=" * 50)

    if all_good:
        print("🎉 All prerequisites met! Ready to launch LangGraph Studio.")
        print("\n🚀 Launch Commands:")
        print("   langgraph up --debugger-port 8123")
        print("   # Access at: http://localhost:8123")
    else:
        print("⚠️  Some prerequisites missing. See installation guide above.")

    return all_good


def main():
    """Main installation and setup function"""
    import argparse

    parser = argparse.ArgumentParser(description="LangGraph Studio Setup")
    parser.add_argument(
        "--check-only", action="store_true", help="Only check prerequisites"
    )
    parser.add_argument(
        "--install-docker", action="store_true", help="Attempt Docker installation"
    )
    args = parser.parse_args()

    # Find project root
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent  # scripts/langgraph/../../

    print("🚀 LangGraph Studio Installation and Setup")
    print(f"📁 Project Root: {project_root}")
    print("=" * 60)

    if args.check_only:
        print_status_report()
        return

    # Installation phase
    print("📦 Installation Phase")
    print("-" * 30)

    # Install LangGraph CLI if needed
    cli_ok, cli_msg = check_langgraph_cli()
    if not cli_ok:
        install_ok, install_msg = install_langgraph_cli()
        print(f"📦 LangGraph CLI: {install_msg}")
        if not install_ok:
            print("❌ Installation failed. Please install manually:")
            print("   pip install langgraph-cli")
            return
    else:
        print(f"✅ LangGraph CLI: {cli_msg}")

    # Create configuration files
    print("\n⚙️  Configuration Phase")
    print("-" * 30)

    config_ok, config_msg = create_langgraph_config(project_root)
    print(f"📝 {config_msg}")

    env_ok, env_msg = create_env_template(project_root)
    print(f"📝 {env_msg}")

    # Docker installation (if requested)
    if args.install_docker:
        print("\n🐳 Docker Installation")
        print("-" * 30)

        docker_ok, docker_msg = check_docker()
        if not docker_ok:
            print("⚠️  Docker installation requires manual setup.")
            print(
                "📥 Download: https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
            )
            print("🔄 After installation, restart and run this script again.")
        else:
            print(f"✅ Docker: {docker_msg}")

    # Final status check
    print("\n" + "=" * 60)
    all_ready = print_status_report()

    if all_ready:
        print("\n💡 Next Steps:")
        print("1. Set your API keys in .env file")
        print("2. Run: langgraph up --debugger-port 8123")
        print("3. Open: http://localhost:8123")
        print("4. Start debugging your workflows visually!")


if __name__ == "__main__":
    main()
