# Session State Typed Models

Implementation plan generated from conversation on 2026-02-28.

## Overview

Replace raw `dict[str, Any]` usage in `SessionState` and its consumers with the typed domain models that already exist (`ChatDocument`, `ChatMetadata`, `ChatMessage`, `RuntimeProfile`). Create one new small model (`RetryAttempt`) for the retry-attempt structure. This enforces the playbook rule: "Never use raw dicts for structured data."

## Requirements

### Core typing

- `SessionState.profile` becomes `RuntimeProfile` (from `domain.profile`), not `dict[str, Any]`.
- `SessionState.chat` becomes `ChatDocument` (from `domain.chat`), not `dict[str, Any]`.
- `SessionState.retry_attempts` becomes `dict[str, RetryAttempt]` where `RetryAttempt` is a new dataclass with fields `user_msg: str`, `assistant_msg: str`, `citations: list[Citation] | None`.
- All parameters and return types currently typed as `dict[str, Any]` for profile or chat data adopt the corresponding model type throughout the call chain.

### Consumer migration

- Every `session.chat.get("messages", [])` becomes `session.chat.messages`.
- Every `session.chat.get("metadata")` / `chat_data["metadata"]` becomes `session.chat.metadata` or `chat_data.metadata`.
- Every `profile["chats_dir"]` / `profile.get("timeout")` becomes `profile.chats_dir` / `profile.timeout`.
- `retry_attempt["user_msg"]` becomes `retry_attempt.user_msg`.

### Message construction

- `orchestration/signals.py` replaces hand-built message dicts with `ChatMessage.new_user()` / `ChatMessage.new_assistant()`.
- `orchestration/message_entry.py` replaces `{"role": "user", "content": user_input}` with `ChatMessage.new_user(user_input).to_dict()` (or passes `ChatMessage` objects if the downstream provider pipeline accepts them).

### Boundary contracts

- Provider-facing message lists (`list[dict]` sent to OpenAI/Anthropic/etc.) remain as `list[dict]` — these are API payloads, not domain objects.
- `to_dict()` / `from_raw()` round-trip methods on domain models remain the serialization boundary.
- `chat/storage.py` continues to read/write JSON via `ChatDocument.from_raw()` and `ChatDocument.to_dict()`.

### Backward compatibility

- `SessionManager.__getitem__` / `__setitem__` dict-like access for diagnostics continues to work via `state_to_dict()` serialization.
- `ContinueAction.chat_data` and `SendAction.chat_data` in `orchestration/types.py` change from `dict[str, Any] | None` to `ChatDocument | None`.

## Architecture

### Existing models (no changes needed)

| Model | Location | Purpose |
|-------|----------|---------|
| `ChatDocument` | `domain/chat.py` | Full chat: metadata + messages |
| `ChatMetadata` | `domain/chat.py` | Title, summary, system_prompt, timestamps |
| `ChatMessage` | `domain/chat.py` | Single message with role, content, model, citations |
| `RuntimeProfile` | `domain/profile.py` | Typed profile with all config fields |
| `Citation` | `ai/types.py` | Citation TypedDict |
| `TokenUsage` | `ai/types.py` | Token usage TypedDict |
| `AIResponseMetadata` | `ai/types.py` | Streaming metadata TypedDict |

### New model

```python
# domain/chat.py (or session/state.py, co-located with retry logic)
@dataclass(slots=True)
class RetryAttempt:
    user_msg: str
    assistant_msg: str
    citations: list[Citation] | None = None
```

### Data flow change

```
Before:  JSON file → dict → SessionState.chat (dict) → consumers do chat["messages"]
After:   JSON file → dict → ChatDocument.from_raw() → SessionState.chat (ChatDocument) → consumers do chat.messages
```

Same pattern for profile:
```
Before:  JSON/YAML → dict → SessionState.profile (dict) → consumers do profile["chats_dir"]
After:   JSON/YAML → dict → RuntimeProfile.from_dict() → SessionState.profile (RuntimeProfile) → consumers do profile.chats_dir
```

## Implementation Steps

### Phase 1: RetryAttempt model (isolated, no cascading changes)

1. **Add `RetryAttempt` dataclass** to `domain/chat.py`. Fields: `user_msg: str`, `assistant_msg: str`, `citations: list[Citation] | None = None`.
2. **Update `SessionState.retry_attempts`** type from `dict[str, dict[str, Any]]` to `dict[str, RetryAttempt]`.
3. **Update `session/operations.py`** `add_retry_attempt` to construct `RetryAttempt` instead of a dict.
4. **Update `orchestration/signals.py`** `build_retry_replacement_plan` to accept `RetryAttempt` and use attribute access. Also use `ChatMessage.new_user()` / `ChatMessage.new_assistant()` for building replacement messages.
5. **Update `session_manager.py`** retry method signatures (`get_retry_attempt` returns `RetryAttempt | None`).
6. **Fix tests** touching retry attempt creation/consumption.

### Phase 2: Profile dict → RuntimeProfile

7. **Update `SessionState.profile`** type from `dict[str, Any]` to `RuntimeProfile`.
8. **Update `SessionManager.__init__`** to call `RuntimeProfile.from_dict(profile)` and store the result.
9. **Update `SessionManager.profile` descriptor** type from `StateField[dict[str, Any]]` to `StateField[RuntimeProfile]`.
10. **Migrate `session_manager.py` internal access** — `profile["timeout"]` → `profile.timeout`, `profile["api_keys"]` → `profile.api_keys`, etc.
11. **Migrate `ai/runtime.py`** — `session.profile["api_keys"]` → `session.profile.api_keys`.
12. **Migrate `ai/helper_runtime.py`** — `profile["api_keys"]` → `profile.api_keys`.
13. **Migrate `ai/limits.py`** — `profile.get("ai_limits")` → `profile.ai_limits`.
14. **Migrate `timeouts.py`** — `profile.get("timeout")` → `profile.timeout`.
15. **Migrate `repl/loop.py`** — `manager.profile.get("chats_dir")` → `manager.profile.chats_dir`, etc.
16. **Migrate `commands/` modules** — `manager.profile["models"]` → `manager.profile.models`, `manager.profile["chats_dir"]` → `manager.profile.chats_dir`, etc. Files: `chat_files.py`, `runtime_models.py`, `runtime_modes.py`, `meta_generation.py`, `base.py`.
17. **Handle `set_timeout` mutation** — `self._state.profile["timeout"] = normalized` must become `self._state.profile.timeout = normalized` (requires `RuntimeProfile` to be mutable, which it is as a non-frozen dataclass).
18. **Fix tests** touching profile dict access patterns.

### Phase 3: Chat dict → ChatDocument

19. **Update `SessionState.chat`** type from `dict[str, Any]` to `ChatDocument`.
20. **Update `SessionManager.__init__`** to wrap incoming chat dict with `ChatDocument.from_raw()` (or `ChatDocument.empty()` when None).
21. **Update `SessionManager.chat` descriptor** type.
22. **Update `session/state.py` functions** — `initialize_message_hex_ids`, `assign_new_message_hex_id`, `has_pending_error` to operate on `ChatDocument`.
23. **Update `session/operations.py`** — `switch_chat` receives `ChatDocument`, `close_chat` sets `state.chat = ChatDocument.empty()`, message access via `.messages` / `.metadata`.
24. **Update `orchestration/types.py`** — `ContinueAction.chat_data` and `SendAction.chat_data` become `ChatDocument | None`.
25. **Update `orchestration/signals.py`** — `current_chat_data.get("messages", [])` → `current_chat_data.messages`.
26. **Update `orchestration/response_handlers.py`** — all `chat_data["messages"]` / `chat_data.get("messages")` → `chat_data.messages`.
27. **Update `orchestration/message_entry.py`** — `chat_data["messages"]` → `chat_data.messages`, `chat_data.get("messages", [])` → `chat_data.messages`.
28. **Update `orchestration/chat_switching.py`** — message count via `len(new_chat_data.messages)`.
29. **Update `repl/loop.py`** — `chat_data["metadata"]` → `chat_data.metadata`, `chat_data.get("messages", [])` → `chat_data.messages`.
30. **Update `commands/` modules** — `meta_generation.py`, `meta_inspection.py`, `runtime_mutation.py`, `runtime_modes.py`: all `chat_data["messages"]` → `chat_data.messages`.
31. **Update `chat/storage.py`** — ensure `save_chat` accepts `ChatDocument` and calls `.to_dict()` for JSON serialization.
32. **Update `chat/messages.py`** — `add_user_message`, `get_messages_for_ai`, etc. to operate on `ChatDocument`.
33. **Fix tests** touching chat dict access patterns.

### Phase 4: Cleanup and verification

34. **Remove dead `isinstance(…, dict)` guards** that were protecting against the old untyped dicts.
35. **Run `ruff`** to check for unused imports and style issues.
36. **Run `mypy`** to verify type consistency across the migrated call chain.
37. **Run `pytest`** full suite to confirm no regressions.

## Open Questions

- **Provider message format:** The provider pipeline (`ai/runtime.py`, individual providers) receives `list[dict]` as the API wire format. Should this remain as-is (with `ChatMessage.to_dict()` at the boundary), or should providers accept `list[ChatMessage]` and handle their own serialization? Keeping `list[dict]` at the provider boundary is simpler and matches third-party SDK expectations.
- **`chat/messages.py` module role:** Functions like `add_user_message` currently mutate a dict in-place. With `ChatDocument`, these become methods on `ChatDocument` or thin wrappers that mutate `ChatDocument.messages`. Decide whether to keep the module as a façade or fold the logic into `ChatDocument` methods.
- **`profile.py` (loader module) vs `domain/profile.py`:** The loader in `profile.py` does validation and path resolution on a raw dict before `RuntimeProfile.from_dict()` is called. Confirm that `RuntimeProfile.from_dict()` should remain the single parse entry point and the loader continues to pre-process the raw dict before handing it off.
- **`SessionManager` dict-like access:** `__getitem__` / `__setitem__` currently expose raw state. After this change, `manager["profile"]` would return a `RuntimeProfile` object. Is this acceptable, or should `to_dict()` be called lazily for backward compat in tests?
