#!/bin/bash

# Install tk CLI app using Poetry
# This script ensures Poetry is installed, then installs the tk app dependencies

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

echo ""
echo "=== tk Installation ==="
echo ""
echo "Project directory: $PROJECT_DIR"
echo ""

# Check if Poetry is installed
if command -v poetry &> /dev/null; then
    echo "✓ Poetry is installed"
else
    echo "✗ Poetry is not installed"
    echo ""
    echo "Please install Poetry first:"
    echo "  brew install poetry"
    echo ""
    exit 1
fi

# Navigate to project directory
cd "$PROJECT_DIR"

# Install dependencies
echo ""
echo "Installing dependencies with Poetry..."
if poetry install; then
    echo "✓ Dependencies installed"
else
    echo "✗ Failed to install dependencies"
    echo ""
    exit 1
fi

echo ""
echo "=== Installation Complete! ==="
echo ""
echo "To use tk:"
echo "  poetry run tk --profile ~/path/to/profile.json"
echo ""
echo "Or activate the virtual environment first:"
echo "  cd $PROJECT_DIR"
echo "  poetry shell"
echo "  tk --profile ~/path/to/profile.json"
echo ""
