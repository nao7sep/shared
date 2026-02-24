#!/bin/zsh
cd "$(dirname "$0")/.."
uv sync --group dev
uv run mypy --strict --follow-imports=skip \
  src/polychat/domain/chat.py \
  src/polychat/domain/profile.py \
  src/polychat/commands/command_docs.py \
  src/polychat/commands/command_docs_data.py \
  src/polychat/commands/command_docs_models.py \
  src/polychat/ai/provider_logging.py \
  src/polychat/ai/provider_utils.py \
  src/polychat/logging/schema.py \
  src/polychat/logging/sanitization.py
