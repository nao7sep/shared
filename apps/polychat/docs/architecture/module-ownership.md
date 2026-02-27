# PolyChat Module Ownership

This document defines package-level ownership boundaries after the 2026-02 refactor.

## Package Boundaries

- `src/polychat/ai/`
  - Owns provider integrations, model catalog/capabilities/pricing, request limits, AI cost estimation, and runtime orchestration (`runtime.py`, `helper_runtime.py`).
  - `citations.py` owns citation normalization and redirect-resolution runtime helpers.
  - `provider_utils.py` owns shared provider-side message formatting helpers.
  - `provider_logging.py` owns shared provider error log emission/message helpers.

- `src/polychat/domain/`
  - Owns typed boundary models used by persistence and runtime adapters.
  - Current domain models:
    - `chat.py` (`ChatDocument`, `ChatMetadata`, `ChatMessage`)
    - `profile.py` (`RuntimeProfile`)

- `src/polychat/chat/`
  - Owns persisted chat storage schema, chat message mutations, and chat-file operations.
  - Root `chat_manager.py` is a compatibility facade over `chat/files.py`.

- `src/polychat/session/`
  - Owns session state model and session-scoped operations (mode state, provider cache, persistence, lifecycle helpers).
  - `operations.py` owns consolidated session runtime operations (chat lifecycle, modes, hex-id mutations, persistence, cache, settings, and system prompt loading).
  - `accessors.py` owns SessionManager state access descriptors (`StateField`) and dict/snapshot helper functions.
  - `session_manager.py` is the public facade/composition entry for session operations.

- `src/polychat/orchestration/`
  - Owns REPL orchestration flow handlers:
    - shared orchestration action/transition types (`types.py`)
    - command signals (`signals.py`, dispatch table + payload validation + retry-apply replacement policy helpers)
    - chat lifecycle transitions (`chat_switching.py`, new/open/close/rename/delete)
    - user message entry/send action preparation (`message_entry.py`)
    - response/error/cancel post-send mutations and response-mode transition policies (`response_handlers.py`)
  - Root `orchestrator.py` is a thin composer facade.

- `src/polychat/repl/`
  - Owns interactive loop wiring, input/keybindings, status banners, and send pipeline execution.
  - `loop.py` is the consolidated REPL runtime entry that owns prompt/input/banner helpers and main loop control flow.
  - Public entry point is `polychat.repl` package (`repl_loop` re-exported from `repl/__init__.py`).

- `src/polychat/commands/`
  - Owns command handlers and dispatch.
  - `command_docs.py` and `command_docs_data.py` own single-source command documentation metadata/renderers for `/help` and README command listings.
  - `dispatch.py` owns command registration metadata and dispatch orchestration.
  - `context.py` owns explicit command dependency wiring (`CommandContext`).
  - `misc.py` and `chat_files.py` use explicit handler objects with thin adapter mixins for compatibility.
  - `runtime_models.py` and `runtime_modes.py` use explicit handler objects with thin adapter mixins for compatibility.
  - `runtime_mutation.py` uses explicit handler objects with thin adapter mixins for compatibility.
  - `meta_generation.py` and `meta_inspection.py` use explicit handler objects with thin adapter mixins for compatibility.
  - Runtime commands are split into:
    - `runtime_models.py`
    - `runtime_modes.py`
    - `runtime_mutation.py`
  - Metadata commands are split into:
    - `meta_generation.py`
    - `meta_inspection.py`

- `src/polychat/keys/`
  - Owns API key loading/validation and credential backend integrations.
  - `backends.py` owns concrete environment/json/keychain/credential-manager backend helpers.
  - `loader.py` is the public backend-selection/validation API.

- `src/polychat/formatting/`
  - Owns all display and text formatting helpers:
    - `text.py`, `history.py`, `chat_list.py`, `citations.py`, `costs.py`

- `src/polychat/prompts/`
  - Owns prompt template builders (`templates.py`), system-prompt loading (`system_prompt.py`), and prompt assets (`prompts/system/*`).
  - `prompts/__init__.py` re-exports compatibility symbols, including `_load_prompt_from_path` for existing patch points.

- `src/polychat/logging/`
  - Owns logging implementation (`schema.py`, `events.py`, `formatter.py`, `sanitization.py`).

## Facade Policy

- Root-level modules are allowed only when they are:
  - thin entry points (`cli.py`, `orchestrator.py`, `polychat.repl` package entry)
  - thin facades/composition entry points (`chat_manager.py`, `session_manager.py`)
- New domain logic should be added to feature packages, not root facades.

## Refactor Completion Criteria

- No new business logic is added to compatibility facades.
- Internal imports prefer feature-package modules over root facades.
- Legacy shims are removed only after:
  - no in-repo imports depend on them
  - compatibility tests are updated/retired.
- `tests/test_module_boundaries.py` enforces key facade boundaries:
  - `orchestration/*` must not import root `orchestrator` facade.
  - `commands/*` (except package `__init__`) must not import parent `commands` facade.
  - feature modules must not import root `chat_manager` facade.
