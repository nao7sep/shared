#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
rm -rf dist/ build/ .venv/ .coverage
echo "Cleaned."
