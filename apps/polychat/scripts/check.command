#!/bin/zsh
cd "$(dirname "$0")/.."
uv sync --group dev
uv run ruff check src tests
uv run mypy src/polychat
uv run pytest -q
