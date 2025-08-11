#!/usr/bin/env python3
"""
Docker Build Script with Network Resilience
Handles build failures due to network connectivity issues.
"""
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, max_retries=3, delay=5):
    """Run command with retry logic."""
    for attempt in range(max_retries):
        try:
            print(f"🔄 Attempt {attempt + 1}/{max_retries}: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ Command succeeded on attempt {attempt + 1}")
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            print(f"📝 Error output: {e.stderr}")

            if attempt < max_retries - 1:
                print(f"⏳ Waiting {delay} seconds before retry...")
                time.sleep(delay)
            else:
                print(f"🚫 All {max_retries} attempts failed")
                raise


def build_docker_image(
    dockerfile="Dockerfile", tag="universalmas:latest", build_args=None
):
    """Build Docker image with network resilience."""
    print("🚀 Starting Docker build with network resilience...")

    # Basic build command
    cmd = ["docker", "build", "-f", dockerfile, "-t", tag]

    # Add build args if provided
    if build_args:
        for key, value in build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])

    # Add current directory
    cmd.append(".")

    try:
        # Try build with retry logic
        run_command(cmd, max_retries=3, delay=10)
        print(f"✅ Successfully built {tag}")
        return True

    except subprocess.CalledProcessError:
        print(f"❌ Failed to build {tag} after all retries")

        # Try alternative build strategy
        print("🔄 Attempting alternative build strategy...")
        return build_with_alternative_strategy(dockerfile, tag, build_args)


def build_with_alternative_strategy(dockerfile, tag, build_args=None):
    """Alternative build strategy for network issues."""
    print("🔧 Using alternative build strategy with BuildKit disabled...")

    # Disable BuildKit for better network handling
    env = {"DOCKER_BUILDKIT": "0"}

    cmd = ["docker", "build", "--no-cache", "-f", dockerfile, "-t", tag]

    if build_args:
        for key, value in build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])

    cmd.append(".")

    try:
        print(f"🔄 Running alternative build: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, env={**subprocess.os.environ, **env})
        print(f"✅ Alternative build succeeded for {tag}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Alternative build also failed: {e}")
        return False


def main():
    """Main build orchestration."""
    print("🐳 Universal MAS Framework - Docker Build Script")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path("Dockerfile").exists():
        print("❌ Dockerfile not found in current directory")
        sys.exit(1)

    # Build production image
    print("📦 Building production image...")
    if not build_docker_image("Dockerfile", "universalmas:latest"):
        print("❌ Production build failed")
        sys.exit(1)

    # Build development image if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--dev":
        print("📦 Building development image...")
        if not build_docker_image("Dockerfile.dev", "universalmas:dev"):
            print("❌ Development build failed")
            sys.exit(1)

    print("🎉 All Docker builds completed successfully!")

    # Show image information
    try:
        result = subprocess.run(
            ["docker", "images", "universalmas"],
            capture_output=True,
            text=True,
            check=True,
        )
        print("\n📋 Built images:")
        print(result.stdout)
    except subprocess.CalledProcessError:
        print("⚠️ Could not list Docker images")


if __name__ == "__main__":
    main()
