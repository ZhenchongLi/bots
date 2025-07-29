#!/bin/bash

# OpenAI Proxy Service Test Runner
echo "Running OpenAI Proxy Service Tests..."
echo "======================================"

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Check if .env.test exists
if [ ! -f ".env.test" ]; then
    echo "❌ Test environment file (.env.test) not found!"
    echo "Please make sure .env.test exists in the project root."
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "✅ Using uv virtual environment..."
    echo "✅ Using test configuration from .env.test"
else
    echo "❌ Virtual environment not found. Please run 'uv sync --group dev' first."
    exit 1
fi

# Run tests with coverage
echo ""
echo "Running unit tests with coverage..."
echo "Test configuration: .env.test"
echo "Database: In-memory SQLite"
echo "API Base URL: https://api.test-openai.com/v1"
echo ""

uv run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html:htmlcov

# Check if tests passed
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "Coverage report generated in htmlcov/index.html"
    echo "You can open it in your browser to see detailed coverage information."
else
    echo ""
    echo "❌ Some tests failed. Please check the output above."
    exit 1
fi

# Optional: Run specific test categories
echo ""
echo "Test categories available:"
echo "  uv run pytest tests/ -m unit        # Run only unit tests"
echo "  uv run pytest tests/ -m integration # Run only integration tests"
echo "  uv run pytest tests/test_api.py     # Run specific test file"
echo "  uv run pytest tests/ -k test_health # Run tests matching pattern"