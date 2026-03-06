#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --group dev
uv run pytest tests/ -v
