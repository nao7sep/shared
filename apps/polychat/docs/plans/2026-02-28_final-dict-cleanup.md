# PolyChat Final Dict-to-Type Cleanup

Implementation plan generated from conversation on 2026-02-28.

## Overview

Eliminate all remaining internal `dict` usage that should be named types, remove
all backward-compatibility patterns (sole user, no external consumers), and clean
up comments/docstrings that unnecessarily reference "dict." After this pass, every
`dict` remaining in the codebase will have a clear, documented reason to stay.

## Requirements

### Core Typing

- `hex_id.build_hex_map()` must stop accepting raw dicts; use `ChatMessage`
  attribute access only.
- `hex_id.get_message_index()` and `get_hex_id()` must accept `list[ChatMessage]`
  instead of `list[dict[str, Any]]`.
- All callers that convert `[m.to_dict() for m in messages]` just to call hex_id
  functions must pass `ChatMessage` lists directly and use attribute access for
  role checks.
- `add_assistant_message()` citations parameter must use `list[Citation]` (the
  TypedDict already exists in `ai/types.py`), not `list[dict[str, Any]]`.
- `add_retry_attempt()` citations parameter must use `list[Citation]`.
- `_sync_in_memory_metadata()` must accept `ChatMetadata` instead of
  `dict[str, Any]`.
- `resolve_profile_limits()` and `resolve_request_limits()` must accept
  `RuntimeProfile | None`, not `RuntimeProfile | Mapping[str, Any] | None`.

### Backward Compatibility Removal

- `SessionManager.__init__()` must require `RuntimeProfile` for `profile` and
  `ChatDocument | None` for `chat`. No dict-to-type conversion in the
  constructor.
- `SessionManager.__getitem__`, `__setitem__`, `get()` (dict-emulation methods
  used only by tests) must be removed. Tests must use direct attribute access.
- `SessionState.get_cached_provider()` backward-compat fallback (line 81-82 in
  state.py) must be removed.
- All 87 test sites that pass `profile={...}` must construct `RuntimeProfile`.
- All 12 test sites that pass `chat={...}` must construct `ChatDocument`.
- `test_session_state.py` `TestSessionDictDuality` class documents a dead
  pattern and must be removed.

### Comment/Docstring Cleanup

- Remove "dict-like" from `session/accessors.py` module docstring and
  `session_manager.py` class docstring.
- Rename section header "Dict-Like Access (Backward Compatibility)" since the
  section will contain only `to_dict()` after cleanup.
- Remove "(dict-like access)" from remaining docstrings.
- Fix `domain/chat.py` module docstring.
- Fix `ai/citations.py` comment "Output dict key order."
- Fix `setup_wizard.py` "Build profile dictionary" docstring.
- Remove "backward-compat" comments from `state.py` and `session_manager.py`.

## Remaining Dicts — Rationale for Each

Every `dict` below stays because it falls into one of three categories:
**serialization boundary** (converting to/from JSON), **provider boundary**
(data shaped by external AI SDK contracts), or **genuinely open-ended** (schema
varies or is unknown at compile time).

| Location | Type annotation | Why it stays |
|---|---|---|
| `ChatMessage.to_dict()` return | `dict[str, Any]` | **Serialization** — JSON file output |
| `ChatMessage.from_raw()` input | raw `dict` | **Serialization** — JSON file input |
| `ChatMetadata.to_dict()` / `from_raw()` | same | **Serialization** |
| `ChatDocument.to_dict()` / `from_raw()` | same | **Serialization** |
| `RuntimeProfile.to_dict()` / `from_dict()` | same | **Serialization** |
| `profile.validate_profile()` param | `dict[str, Any]` | **Pre-parse** — validates raw JSON before conversion |
| `profile.create_profile()` return | `tuple[dict, list[str]]` | **Serialization** — builds JSON for file write |
| `setup_wizard._build_profile()` return | `dict` | **Serialization** — feeds into JSON write |
| `chat/storage` internal functions | `dict[str, Any]` | **Serialization** — change detection on JSON payloads |
| `get_messages_for_ai()` return | `list[dict[str, Any]]` | **Provider boundary** — exact shape required by SDKs |
| `get_retry_context_for_last_interaction()` | `list[dict[str, Any]]` | **Provider boundary** — same; feeds into SDK calls |
| `SendAction.messages` | `list[dict[str, Any]]` | **Provider boundary** — dispatch payload for providers |
| `message_entry._build_send_action` | `messages: list[dict]` | **Provider boundary** |
| `HelperAIInvoker.messages` | `list[dict]` | **Provider boundary** — helper AI SDK calls |
| `_invoke_helper_ai` messages param | `list[dict]` | **Provider boundary** |
| `enter_retry_mode` / `get_retry_context` | `list[dict]` | **Provider boundary** — frozen SDK-ready context |
| `enter_secret_mode` / `get_secret_context` | `list[dict]` | **Provider boundary** — frozen SDK-ready context |
| `SessionState.retry_base_messages` | `list` | **Provider boundary** — stores SDK-ready messages |
| `SessionState.secret_base_messages` | `list` | **Provider boundary** |
| Provider `format_messages` / `send_*` | `list[dict]` | **Provider boundary** — SDK contract |
| `estimate_message_chars()` | `messages: list[dict]` | **Provider boundary** — operates on SDK-ready messages |
| `logging/formatter.py` internals | `dict[str, Any]` | **Serialization** — log record assembly |
| `logging/events.py` helpers | `dict[str, Any]` | **Serialization** — log payload construction |
| `logging/schema.py` key order | `dict[str, list[str]]` | Simple str→list registry |
| `ChatMessage.details` | `dict[str, Any] \| None` | **Provider boundary** — error details vary per provider |
| `ChatMessage.extras` | `dict[str, Any]` | **Open-ended** — future/unknown fields from JSON |
| `ChatMetadata.extras` | `dict[str, Any]` | **Open-ended** — same |
| `RuntimeProfile.extras` | `dict[str, Any]` | **Open-ended** — user extension point |
| `RuntimeProfile.models` | `dict[str, str]` | Simple str→str mapping; key set varies |
| `RuntimeProfile.api_keys` | `dict[str, dict[str, Any]]` | Per-provider config; inner dict typed as `KeyConfig` at call site |
| `RuntimeProfile.ai_limits` | `dict[str, Any] \| None` | Nested config with raw values needing normalization; typed output is `AIRequestLimits` |
| `SessionState.retry_attempts` | `dict[str, RetryAttempt]` | Simple str→typed-value mapping |
| `SessionState._provider_cache` | `dict[tuple, Any]` | Cache keyed by tuple; values are provider instances |
| `SessionManager.message_hex_ids` | `dict[int, str]` | Simple int→str mapping |
| `hex_id.assign_hex_ids` return | `dict[int, str]` | Simple int→str mapping |
| `ai/catalog.py` registries | `dict[str, list[str]]` / `dict[str, str]` | Simple registries |
| `ai/tools.py` tool configs | `dict[str, str]` | **Provider boundary** — SDK tool definitions |
| `keys/backends.py` JSON traversal | `isinstance(value, dict)` | **Serialization** — parsing nested JSON |
| `commands/dispatch.py` command map | `dict[str, CommandCallable]` | Simple str→callable mapping |
| `response_handlers.py` citations cast | removed in this plan | — |

## Architecture

No new modules. Changes are surgical edits within existing files.

**Key structural decisions:**
- `hex_id` functions will accept `list[ChatMessage]` via the existing
  `ChatMessage` import (no circular dependency — `hex_id.py` already imports
  nothing from domain).
- Test helper: introduce a `_make_profile(**overrides)` factory in `conftest.py`
  to reduce boilerplate when constructing `RuntimeProfile` in tests.
- `SessionManager.__getitem__`/`__setitem__`/`get()` are removed; `to_dict()`
  stays (serialization for diagnostics).

## Implementation Steps

Steps are ordered to minimize cascading test failures.

1. **Create test helper `_make_profile`** in `tests/conftest.py`.
   A factory that builds a `RuntimeProfile` with sensible defaults, accepting
   keyword overrides. This makes step 7 (mass test migration) manageable.

2. **Fix `hex_id.py` signatures.**
   - `build_hex_map`: remove `isinstance(message, dict)` branch; use only
     `getattr(message, "hex_id", None)`.
   - `get_message_index`: change `list[dict[str, Any]]` to `list[ChatMessage]`.
   - `get_hex_id`: same.
   - Remove `Any` import.

3. **Update hex_id callers to pass ChatMessage lists.**
   - `commands/runtime_mutation.py`: remove `[m.to_dict() ...]`, use
     `chat_data.messages` directly, access `.role` attribute instead of
     `.get("role")`.
   - `commands/meta_generation.py:183-184`: pass `messages` directly.
   - `commands/meta_inspection.py:121`: pass `messages` directly.

4. **Fix citation typing chain.**
   - `chat/messages.py` `add_assistant_message`: change `citations` param from
     `list[dict[str, Any]]` to `list[Citation] | None`. Remove manual
     normalization (caller already provides `Citation` objects).
   - `session/operations.py` `add_retry_attempt`: change `citations` param to
     `list[Citation] | None`.
   - `session_manager.py` `add_retry_attempt`: same.
   - `response_handlers.py`: remove `cast(Optional[list[dict[str, Any]]], ...)`
     calls.

5. **Fix `_sync_in_memory_metadata` typing.**
   - Change param from `dict[str, Any]` to `ChatMetadata`.
   - Update both call sites in `chat/storage.py`.

6. **Fix `resolve_profile_limits` / `resolve_request_limits` signatures.**
   - Remove `Mapping[str, Any]` alternative; accept `RuntimeProfile | None` only.
   - Remove the `isinstance(profile, Mapping)` branch.

7. **Remove SessionManager backward-compat patterns.**
   - Constructor: `profile` param → `RuntimeProfile` only.
   - Constructor: `chat` param → `ChatDocument | None` only.
   - Remove dict-backfill logic in `__init__`.
   - Remove `__getitem__`, `__setitem__`, `get()`.
   - Remove `state_getitem`, `state_setitem`, `state_get` from
     `session/accessors.py`.

8. **Remove `SessionState.get_cached_provider` backward-compat fallback.**
   - Delete the 2-tuple fallback lookup and its comment.

9. **Migrate tests.**
   - Replace all `profile={...}` with `_make_profile(...)`.
   - Replace all `chat={...}` with `ChatDocument.from_raw(...)`.
   - Remove `TestSessionDictDuality` class.
   - Update tests that use `manager["key"]` to use `manager.key`.
   - Rename test methods/docstrings that mention "backward compatibility" or
     "dict-like."

10. **Comment and docstring cleanup.**
    - `session/accessors.py` line 1: "Session access descriptors and state
      helpers for SessionManager."
    - `session_manager.py` class docstring: remove "dict-like".
    - `session_manager.py` section header: "Serialization" (only `to_dict`
      remains).
    - `session_manager.py` `to_dict` docstring: remove "dict-like access".
    - `domain/chat.py` line 1: "Typed chat domain models."
    - `ai/citations.py` line 157: rephrase "Output dict key order."
    - `setup_wizard.py` line 137: "Build profile from collected API keys."
    - `session/state.py`: remove "Backward-compat" comment.

11. **Verify.** Run `ruff check` and `pytest` to confirm nothing is broken.

## Open Questions

- `RuntimeProfile.ai_limits` is `dict[str, Any] | None` with a known nested
  structure (`default`, `providers`, `helper`). A `TypedDict` could describe it,
  but the raw values within each block need normalization before use, so the
  typed output is already `AIRequestLimits`. Adding a raw config TypedDict would
  add a type that doesn't match reality until after normalization. Kept as
  `dict[str, Any]` for now. Revisit if the structure grows.
- `RuntimeProfile.api_keys` inner values are `dict[str, Any]` but have a
  corresponding `KeyConfig` TypedDict. Changing `api_keys` to
  `dict[str, KeyConfig]` would require ensuring `from_dict` normalizes each
  entry into a proper `KeyConfig`. Currently they are structurally compatible
  but not explicitly typed. Left as-is to limit cascade; the `KeyConfig` type
  is used where it matters (at the `load_api_key` call site).
