#!/bin/bash

# Clean build artifacts from polychat project
# Removes .venv, __pycache__, .pyc files, .pytest_cache, .ruff_cache

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

echo ""
echo "=== polychat Cleanup ==="
echo ""
echo "Project directory: $PROJECT_DIR"
echo ""

# Navigate to project directory
cd "$PROJECT_DIR"

# Remove .venv directory
if [ -d ".venv" ]; then
    echo "Removing .venv directory..."
    rm -rf .venv
    echo "✓ Removed .venv"
else
    echo "✓ No .venv directory found"
fi

# Remove __pycache__ directories
echo ""
echo "Removing __pycache__ directories..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYCACHE_COUNT" -gt 0 ]; then
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo "✓ Removed $PYCACHE_COUNT __pycache__ directories"
else
    echo "✓ No __pycache__ directories found"
fi

# Remove .pyc files
echo ""
echo "Removing .pyc files..."
PYC_COUNT=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYC_COUNT" -gt 0 ]; then
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo "✓ Removed $PYC_COUNT .pyc files"
else
    echo "✓ No .pyc files found"
fi

# Remove .pytest_cache directory
echo ""
if [ -d ".pytest_cache" ]; then
    echo "Removing .pytest_cache directory..."
    rm -rf .pytest_cache
    echo "✓ Removed .pytest_cache"
else
    echo "✓ No .pytest_cache directory found"
fi

# Remove .ruff_cache directory
echo ""
if [ -d ".ruff_cache" ]; then
    echo "Removing .ruff_cache directory..."
    rm -rf .ruff_cache
    echo "✓ Removed .ruff_cache"
else
    echo "✓ No .ruff_cache directory found"
fi

# Remove .mypy_cache directory
echo ""
if [ -d ".mypy_cache" ]; then
    echo "Removing .mypy_cache directory..."
    rm -rf .mypy_cache
    echo "✓ Removed .mypy_cache"
else
    echo "✓ No .mypy_cache directory found"
fi

# Remove dist directory
echo ""
if [ -d "dist" ]; then
    echo "Removing dist directory..."
    rm -rf dist
    echo "✓ Removed dist"
else
    echo "✓ No dist directory found"
fi

# Remove .claude directory
echo ""
if [ -d ".claude" ]; then
    echo "Removing .claude directory..."
    rm -rf .claude
    echo "✓ Removed .claude"
else
    echo "✓ No .claude directory found"
fi

echo ""
echo "=== Cleanup Complete! ==="
echo ""
