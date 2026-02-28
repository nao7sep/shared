#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync
uv run tk --profile "$HOME/code/shared/apps/tk/data/profile.json"
