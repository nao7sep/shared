#!/bin/zsh
SHARED_AGENTS="$(dirname "$0")/../.claude/agents"
GLOBAL_AGENTS="$HOME/.claude/agents"

mkdir -p "$GLOBAL_AGENTS"

find "$GLOBAL_AGENTS" -maxdepth 1 -name "*.md" -delete
cp "$SHARED_AGENTS"/*.md "$GLOBAL_AGENTS/"

COUNT=$(find "$SHARED_AGENTS" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
echo "Synced $COUNT agents to ~/.claude/agents."
