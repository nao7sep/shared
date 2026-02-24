#!/bin/zsh
cd "$(dirname "$0")/.."
uv tool uninstall revzip 2>/dev/null || echo "revzip was not installed via uv tool."
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type d -name "*.egg-info" -prune -exec rm -rf {} +
find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
rm -rf dist/ build/ .venv/
echo "Cleaned."
