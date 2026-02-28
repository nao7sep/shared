#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Clean project artifacts"
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
rm -rf dist/ .venv/ .claude/
echo ""
echo "Removed cache and build artifacts."
