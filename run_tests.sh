#!/bin/bash
# Test runner script for playlist-builder

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PLAYLIST-BUILDER TEST SUITE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Ensure we're in the repo directory
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# Check if .venv exists in repo
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in repo..."
    python3 -m venv .venv
    echo "Installing dependencies..."
    .venv/bin/pip install -q --upgrade pip
    .venv/bin/pip install -q -r requirements.txt
    .venv/bin/pip install -q -r requirements-test.txt
fi

# Use repo's venv
PYTEST=".venv/bin/pytest"

# Run tests
echo "Running test suite from repo directory..."
echo ""

# Run with coverage if pytest-cov is available
if .venv/bin/python3 -c "import pytest_cov" 2>/dev/null; then
    $PYTEST --cov=. --cov-report=term-missing --cov-report=html -v
    echo ""
    echo "Coverage report generated in htmlcov/index.html"
else
    $PYTEST -v
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Tests complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

