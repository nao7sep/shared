#!/bin/zsh
cd "$(dirname "$0")/.."
uv run tk --profile "$HOME/code/shared/apps/tk/data/profile.json"
