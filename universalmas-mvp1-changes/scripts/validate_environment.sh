#!/bin/bash
# scripts/validate_environment.sh

set -e

echo "🔍 Validating Universal Framework Environment..."

# Test Docker build
echo "📦 Testing Docker build..."
docker build -t universal-framework-test .

# Test dependency installation
echo "🔧 Testing dependency installation..."
docker run --rm universal-framework-test python -c "
import fastapi
import langchain
import langgraph
import pydantic
import pytest
import mypy
print('✅ All core dependencies imported successfully')
"

# Test type checking
echo "🔎 Testing type checking..."
docker run --rm universal-framework-test mypy --version

# Test code formatting
echo "🎨 Testing code formatting..."
docker run --rm universal-framework-test black --version

# Test linting
echo "🧹 Testing linting..."
docker run --rm universal-framework-test ruff --version

# Test pytest
echo "🧪 Testing pytest..."
docker run --rm universal-framework-test pytest --version

echo "✅ Environment validation complete!"
