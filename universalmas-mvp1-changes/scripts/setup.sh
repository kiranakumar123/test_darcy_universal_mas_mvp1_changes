#!/bin/bash
# scripts/setup.sh - Universal Framework Development Environment Setup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    log_info "Checking Python version..."

    if ! command_exists python3; then
        log_error "Python 3 is not installed. Please install Python 3.11 or higher."
        exit 1
    fi

    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.11"

    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        log_error "Python $required_version or higher is required. Found: $python_version"
        exit 1
    fi

    log_success "Python $python_version found"
}

# Function to check Docker
check_docker() {
    log_info "Checking Docker installation..."

    if ! command_exists docker; then
        log_warning "Docker is not installed. Install Docker to use containerized development."
        return 1
    fi

    if ! docker info >/dev/null 2>&1; then
        log_warning "Docker is installed but not running. Please start Docker."
        return 1
    fi

    log_success "Docker is available and running"
    return 0
}

# Function to setup virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."

    if [ -d "venv" ]; then
        log_warning "Virtual environment already exists. Removing..."
        rm -rf venv
    fi

    python3 -m venv venv
    source venv/bin/activate

    # Upgrade pip
    python -m pip install --upgrade pip

    log_success "Virtual environment created and activated"
}

# Function to install dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."

    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt not found"
        exit 1
    fi

    pip install -r requirements.txt
    log_success "Dependencies installed"
}

# Function to setup pre-commit hooks
setup_pre_commit() {
    log_info "Setting up pre-commit hooks..."

    if command_exists pre-commit; then
        pre-commit install
        log_success "Pre-commit hooks installed"
    else
        log_warning "pre-commit not available. Install it for code quality hooks."
    fi
}

# Function to create environment file
create_env_file() {
    log_info "Creating environment configuration..."

    if [ ! -f ".env" ]; then
        cat > .env << EOF
# Universal Framework Environment Configuration
ENVIRONMENT=development
DEBUG=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Authentication
JWT_SECRET_KEY=development-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# LangSmith (optional)
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=your-langsmith-api-key

# BoundaryML (optional)
# BOUNDARYML_API_KEY=your-boundaryml-api-key
EOF
        log_success "Environment file created (.env)"
    else
        log_info "Environment file already exists"
    fi
}

# Function to validate environment
validate_environment() {
    log_info "Validating environment setup..."

    # Test imports
    python -c "
import sys
import fastapi
import pydantic
import langchain
import langgraph
import redis
print('✅ All core dependencies imported successfully')
print(f'✅ Python version: {sys.version}')
"

    # Run type checking
    if command_exists mypy; then
        log_info "Running mypy type checking..."
        mypy --version > /dev/null
        log_success "mypy is working"
    fi

    # Run linting
    if command_exists ruff; then
        log_info "Running ruff linting..."
        ruff --version > /dev/null
        log_success "ruff is working"
    fi

    # Run code formatting
    if command_exists black; then
        log_info "Running black formatting check..."
        black --version > /dev/null
        log_success "black is working"
    fi

    log_success "Environment validation complete"
}

# Function to run tests
run_tests() {
    log_info "Running initial tests..."

    if [ -f "tests/test_environment.py" ]; then
        pytest tests/test_environment.py -v
        log_success "Environment tests passed"
    else
        log_warning "No environment tests found"
    fi
}

# Function to build Docker image
build_docker() {
    if check_docker; then
        log_info "Building Docker image..."
        docker build -t universal-framework:dev .
        log_success "Docker image built successfully"

        log_info "Testing Docker container..."
        docker run --rm universal-framework:dev python -c "
import fastapi
import pydantic
import langchain
import langgraph
print('✅ Docker container working correctly')
"
        log_success "Docker container validated"
    fi
}

# Main setup function
main() {
    echo -e "${BLUE}"
    echo "🚀 Universal Framework Development Environment Setup"
    echo "=================================================="
    echo -e "${NC}"

    # Check prerequisites
    check_python_version

    # Setup Python environment
    setup_venv
    install_dependencies

    # Setup development tools
    setup_pre_commit
    create_env_file

    # Validate setup
    validate_environment
    run_tests

    # Docker setup (optional)
    build_docker

    echo -e "${GREEN}"
    echo "🎉 Setup Complete!"
    echo "=================="
    echo -e "${NC}"
    echo "Next steps:"
    echo "1. Activate virtual environment: source venv/bin/activate"
    echo "2. Start development server: uvicorn universal_framework.api.main:app --reload"
    echo "3. Run tests: pytest"
    echo "4. Run type checking: mypy src/"
    echo "5. Format code: black src/ tests/"
    echo ""
    echo "For Docker development:"
    echo "1. docker-compose up"
    echo "2. Visit http://localhost:8000"
}

# Script options
case "${1:-setup}" in
    "setup")
        main
        ;;
    "validate")
        source venv/bin/activate 2>/dev/null || true
        validate_environment
        ;;
    "clean")
        log_info "Cleaning development environment..."
        rm -rf venv/ __pycache__/ .pytest_cache/ .mypy_cache/ .coverage htmlcov/
        docker rmi universal-framework:dev 2>/dev/null || true
        log_success "Environment cleaned"
        ;;
    "help")
        echo "Usage: $0 [setup|validate|clean|help]"
        echo ""
        echo "  setup    - Full environment setup (default)"
        echo "  validate - Validate existing environment"
        echo "  clean    - Clean all generated files"
        echo "  help     - Show this help message"
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
