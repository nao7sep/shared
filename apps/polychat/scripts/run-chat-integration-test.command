#!/bin/zsh
cd "$(dirname "$0")/.."
echo "Running PolyChat Chat Integration Test..."
echo ""
uv run pytest tests/test_chat_integration.py -v -s -m integration
