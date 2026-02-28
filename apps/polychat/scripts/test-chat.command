#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --group dev
echo "Running chat integration test..."
echo ""
uv run pytest tests/test_chat_integration.py -v -s -m integration
