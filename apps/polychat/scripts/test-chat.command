#!/bin/zsh
cd "$(dirname "$0")/.."
echo "Running chat integration test..."
echo ""
uv run pytest tests/test_chat_integration.py -v -s -m integration
