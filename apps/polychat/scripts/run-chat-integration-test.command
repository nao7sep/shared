#!/bin/bash
# Quick launcher for chat integration test

cd "$(dirname "$0")/.."

echo "Running PolyChat Chat Integration Test..."
echo ""

poetry run pytest tests/test_chat_integration.py -v -s -m integration
