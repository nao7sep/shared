#!/bin/bash
# Quick launcher for integration test

cd "$(dirname "$0")/.."

echo "Running PolyChat Integration Test..."
echo ""

poetry run pytest tests/test_chat_integration.py -v -s -m integration

echo ""
read -p "Press Enter to close..."
