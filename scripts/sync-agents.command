#!/bin/zsh

SHARED_ROOT="$(dirname "$0")/.."
SOURCE_CLAUDE="$SHARED_ROOT/CLAUDE.md"
COPILOT_INSTRUCTIONS="$SHARED_ROOT/.github/copilot-instructions.md"
SHARED_AGENTS_MD="$SHARED_ROOT/AGENTS.md"
SHARED_AGENTS="$SHARED_ROOT/.claude/agents"
GLOBAL_AGENTS="$HOME/.claude/agents"

mkdir -p "$(dirname "$COPILOT_INSTRUCTIONS")"
cp "$SOURCE_CLAUDE" "$COPILOT_INSTRUCTIONS"
cp "$SOURCE_CLAUDE" "$SHARED_AGENTS_MD"
echo "Copied CLAUDE.md to .github/copilot-instructions.md"
echo "Copied CLAUDE.md to AGENTS.md"

mkdir -p "$GLOBAL_AGENTS"

find "$GLOBAL_AGENTS" -maxdepth 1 -name "*.md" -delete
cp "$SHARED_AGENTS"/*.md "$GLOBAL_AGENTS/"

COUNT=$(find "$SHARED_AGENTS" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
echo "Synced $COUNT agents to ~/.claude/agents."
