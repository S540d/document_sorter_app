#!/bin/bash

# Test runner script for Document Sorter Application
# This script runs different types of tests with appropriate configurations

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
TEST_TYPE="all"
VERBOSE=false
COVERAGE=true
INSTALL_DEPS=false
CLEAN_CACHE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        -i|--install)
            INSTALL_DEPS=true
            shift
            ;;
        -c|--clean)
            CLEAN_CACHE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -t, --type TYPE     Test type: unit, integration, security, performance, all (default: all)"
            echo "  -v, --verbose       Verbose output"
            echo "  --no-coverage       Disable coverage reporting"
            echo "  -i, --install       Install test dependencies"
            echo "  -c, --clean         Clean cache and temporary files"
            echo "  -h, --help          Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

print_status "Running tests from: $PROJECT_ROOT"

# Change to project root
cd "$PROJECT_ROOT"

# Clean cache if requested
if [ "$CLEAN_CACHE" = true ]; then
    print_status "Cleaning cache and temporary files..."
    rm -rf .pytest_cache/
    rm -rf htmlcov/
    rm -rf .coverage
    rm -rf coverage.xml
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    print_success "Cache cleaned"
fi

# Install test dependencies if requested
if [ "$INSTALL_DEPS" = true ]; then
    print_status "Installing test dependencies..."
    if [ -f "requirements-test.txt" ]; then
        pip install -r requirements-test.txt
        print_success "Test dependencies installed"
    else
        print_warning "requirements-test.txt not found, skipping dependency installation"
    fi
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest is not installed. Run with -i to install dependencies or run: pip install pytest"
    exit 1
fi

# Build pytest command
PYTEST_CMD="pytest"

# Add verbose flag if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage options if enabled
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml"
fi

# Function to run specific test types
run_unit_tests() {
    print_status "Running unit tests..."
    $PYTEST_CMD tests/test_*.py -m "not integration and not slow" --tb=short
}

run_integration_tests() {
    print_status "Running integration tests..."
    $PYTEST_CMD tests/test_integration.py -m integration --tb=short
}

run_security_tests() {
    print_status "Running security tests..."

    # Run pytest security tests
    $PYTEST_CMD tests/test_auth.py -m "not slow" --tb=short

    # Run bandit security scan if available
    if command -v bandit &> /dev/null; then
        print_status "Running bandit security scan..."
        bandit -r app/ -f json -o bandit-report.json || print_warning "Bandit found security issues"
    else
        print_warning "bandit not installed, skipping security scan"
    fi

    # Run safety check if available
    if command -v safety &> /dev/null; then
        print_status "Running safety dependency check..."
        safety check || print_warning "Safety found vulnerable dependencies"
    else
        print_warning "safety not installed, skipping dependency check"
    fi
}

run_performance_tests() {
    print_status "Running performance tests..."
    $PYTEST_CMD tests/ -m performance --tb=short
}

# Run tests based on type
case $TEST_TYPE in
    unit)
        run_unit_tests
        ;;
    integration)
        run_integration_tests
        ;;
    security)
        run_security_tests
        ;;
    performance)
        run_performance_tests
        ;;
    all)
        print_status "Running all tests..."

        # Run unit tests first
        if run_unit_tests; then
            print_success "Unit tests passed"
        else
            print_error "Unit tests failed"
            exit 1
        fi

        # Run integration tests
        if run_integration_tests; then
            print_success "Integration tests passed"
        else
            print_error "Integration tests failed"
            exit 1
        fi

        # Run security tests
        if run_security_tests; then
            print_success "Security tests passed"
        else
            print_warning "Security tests completed with warnings"
        fi
        ;;
    *)
        print_error "Unknown test type: $TEST_TYPE"
        print_error "Supported types: unit, integration, security, performance, all"
        exit 1
        ;;
esac

# Show coverage report if enabled
if [ "$COVERAGE" = true ] && [ -f "htmlcov/index.html" ]; then
    print_success "Coverage report generated: htmlcov/index.html"

    # Try to show coverage summary
    if command -v coverage &> /dev/null; then
        print_status "Coverage Summary:"
        coverage report --show-missing | tail -n 10
    fi
fi

print_success "Tests completed successfully!"

# Show additional reports if available
if [ -f "bandit-report.json" ]; then
    print_status "Security report available: bandit-report.json"
fi

if [ -f "coverage.xml" ]; then
    print_status "Coverage XML report available: coverage.xml"
fi