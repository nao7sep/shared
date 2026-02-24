# PolyChat Module Ownership

This document defines package-level ownership boundaries after the 2026-02 refactor.

## Package Boundaries

- `src/polychat/ai/`
  - Owns provider integrations, model catalog/capabilities/pricing, request limits, and AI cost estimation.
  - Runtime send/validate orchestration is still partially rooted in compatibility modules and should converge under `ai/`.

- `src/polychat/chat/`
  - Owns persisted chat storage schema, chat message mutations, and chat-file operations.
  - Root `chat_manager.py` is a compatibility facade over `chat/files.py`.

- `src/polychat/session/`
  - Owns session state model and session-scoped operations (mode state, provider cache, persistence, lifecycle helpers).
  - Root `app_state.py` is a compatibility facade over `session/state.py`.

- `src/polychat/orchestration/`
  - Owns REPL orchestration flow handlers:
    - command signals (`signals.py`)
    - user message entry/send action preparation (`message_entry.py`)
    - response/error/cancel post-send mutations (`response_handlers.py`)
  - Root `orchestrator.py` is a thin composer facade.

- `src/polychat/repl/`
  - Owns interactive loop wiring, input/keybindings, status banners, and send pipeline execution.
  - Public entry point is `polychat.repl` package (`repl_loop` re-exported from `repl/__init__.py`).

- `src/polychat/commands/`
  - Owns command handlers and dispatch.
  - Runtime commands are split into:
    - `runtime_models.py`
    - `runtime_modes.py`
    - `runtime_mutation.py`
  - Metadata commands are split into:
    - `meta_generation.py`
    - `meta_inspection.py`
  - `runtime.py` and `metadata.py` are composition facades.

- `src/polychat/formatting/`
  - Owns all display and text formatting helpers:
    - `text.py`, `history.py`, `chat_list.py`, `citations.py`, `costs.py`
  - Root `text_formatting.py` is a compatibility facade.

- `src/polychat/prompts/`
  - Owns prompt template builders (`templates.py`) and prompt assets (`prompts/system/*`).
  - `prompts/__init__.py` re-exports compatibility symbols, including `_load_prompt_from_path` for existing patch points.

- `src/polychat/logging/`
  - Owns logging implementation.
  - Root `logging_utils.py` is compatibility facade only.

## Facade Policy

- Root-level modules are allowed only when they are:
  - thin entry points (`cli.py`, `orchestrator.py`, `polychat.repl` package entry)
  - compatibility re-export facades (`models.py`, `costs.py`, `text_formatting.py`, `chat_manager.py`, `app_state.py`, `logging_utils.py`)
- New domain logic should be added to feature packages, not root facades.

## Refactor Completion Criteria

- No new business logic is added to compatibility facades.
- Internal imports prefer feature-package modules over root facades.
- Shims are removed only after:
  - no in-repo imports depend on them
  - compatibility tests are updated/retired
  - release notes document breaking import-path changes.
