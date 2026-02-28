# Remaining Dict-to-Type Migration

Implementation plan generated from conversation on 2026-02-28.

## Overview

The first refactor (session-state-typed-models) wired `RuntimeProfile`, `ChatDocument`, and `RetryAttempt` into `SessionState`, eliminating the largest dict violations. However, raw `dict` usage persists in several internal data paths:

1. **`load_profile()` returns `dict[str, Any]`**, causing a cascade of dict-key access across `cli.py`, `repl/loop.py`, and `prompts/system_prompt.py` — all operating on a profile that already has a typed model (`RuntimeProfile`).
2. **`list_chats()` returns `list[dict[str, Any]]`** with 6 fixed fields (`filename`, `path`, `title`, `created_utc`, `updated_utc`, `message_count`) — a textbook case for a dataclass.
3. **Stale `dict` annotations** remain on several functions that already receive `RuntimeProfile` after Phase 2–3 refactoring (e.g., `HelperAIInvoker` protocol, `send_message_to_ai`, `meta_generation._invoke_helper_ai`).
4. **Formatting functions** (`formatting/history.py`, `formatting/text.py`) accept `msg: dict` for chat messages that have a known schema (`ChatMessage`), even when callers have `ChatMessage` objects available.
5. **`KeyConfig`** in `keys/loader.py` is a discriminated union (by `type` field) consumed as raw `dict[str, Any]`.

Provider-facing `list[dict]` (messages sent to AI SDKs), serialization outputs (`to_dict()`), pre-parse validation on raw JSON, and open-ended extension bags (`extras`, `details`) remain as dicts — these are acceptable per the playbook.

## Requirements

### Profile data flow
- `profile.load_profile()` must return `RuntimeProfile` instead of `dict[str, Any]`.
- All consumers (`cli.py`, `repl/loop.py`, `prompts/system_prompt.py`) must use attribute access instead of dict-key access.
- `SessionManager.load_system_prompt()` static method must accept `RuntimeProfile`.
- `SessionManager.__init__` already accepts `RuntimeProfile`; the dict-to-model conversion path in the constructor can be kept for backward compatibility (tests) but the main flow should pass `RuntimeProfile` directly.

### Chat list entries
- `chat/files.py:list_chats()` must return `list[ChatListEntry]` where `ChatListEntry` is a new dataclass.
- All consumers (`formatting/chat_list.py`, `ui/chat_ui.py`) must use attribute access.

### Stale annotations
- `commands/context.py:HelperAIInvoker` protocol: `profile` parameter must be `RuntimeProfile`.
- `commands/meta_generation.py:_invoke_helper_ai`: `profile_data` parameter must be `RuntimeProfile`.
- `ai/runtime.py:send_message_to_ai`: `profile` parameter must be `RuntimeProfile | None`.
- `repl/loop.py:print_startup_banner`: `profile_data` parameter must be `RuntimeProfile`.

### Formatting functions
- `formatting/history.py` message formatters should accept `ChatMessage` instead of `dict`.
- `formatting/text.py:format_messages` should accept `list[ChatMessage]` and `Callable[[ChatMessage], str]`.
- Callers in `meta_inspection.py` and `meta_generation.py` must pass `ChatMessage` objects to formatters (and serialize separately for provider calls).

### API key config (stretch)
- `keys/loader.py:load_api_key` `config` parameter should use a `KeyConfig` TypedDict instead of `dict[str, Any]`.

## Architecture

### New types

**`ChatListEntry`** — dataclass in `domain/chat.py` (co-located with other chat domain types):
```python
@dataclass(slots=True, frozen=True)
class ChatListEntry:
    filename: str
    path: str
    title: str | None
    created_utc: str | None
    updated_utc: str | None
    message_count: int
```

**`KeyConfig`** — TypedDict in `keys/loader.py` (local to the only consumer):
```python
class KeyConfig(TypedDict, total=False):
    type: Required[str]
    key: str
    value: str
    service: str
    account: str
    path: str
```

### Changed return types

| Function | Before | After |
|---|---|---|
| `profile.load_profile()` | `dict[str, Any]` | `RuntimeProfile` |
| `chat.files.list_chats()` | `list[dict[str, Any]]` | `list[ChatListEntry]` |

### Changed parameter types

| Function / Protocol | Parameter | Before | After |
|---|---|---|---|
| `system_prompt.load_system_prompt` | `profile_data` | `dict[str, Any]` | `RuntimeProfile` |
| `SessionManager.load_system_prompt` | `profile_data` | `dict[str, Any]` | `RuntimeProfile` |
| `repl.loop.repl_loop` | `profile_data` | `dict` | `RuntimeProfile` |
| `repl.loop.print_startup_banner` | `profile_data` | `dict` | `RuntimeProfile` |
| `HelperAIInvoker.__call__` | `profile` | `dict[str, Any]` | `RuntimeProfile` |
| `meta_generation._invoke_helper_ai` | `profile_data` | `dict` | `RuntimeProfile` |
| `runtime.send_message_to_ai` | `profile` | `Optional[dict]` | `RuntimeProfile \| None` |
| `keys.loader.load_api_key` | `config` | `dict[str, Any]` | `KeyConfig` |
| `formatting.history.*` | `msg` | `dict` | `ChatMessage` |
| `formatting.text.format_messages` | `messages` | `list[dict]` | `list[ChatMessage]` |
| `formatting.text.format_messages` | `message_formatter` | `Callable[[dict], str]` | `Callable[[ChatMessage], str]` |

### Caller migration for formatting functions

All formatting callers currently serialize `ChatMessage` → dict before passing to formatters. After this refactor, callers pass `ChatMessage` objects directly:

| Caller | Before | After |
|---|---|---|
| `meta_generation.py:77,139` | `format_for_ai_context(get_messages_for_ai(chat_data))` | `format_for_ai_context(chat_data.messages)` |
| `meta_generation.py:193` | `format_for_safety_check([messages_as_dicts[i]])` | `format_for_safety_check([messages[i]])` |
| `meta_generation.py:196` | `format_for_safety_check(messages_as_dicts)` | `format_for_safety_check(chat_data.messages)` |
| `meta_inspection.py:103` | `format_messages([m.to_dict() for m in ...], ...)` | `format_messages(chat_data.messages, ...)` |
| `meta_inspection.py:120,142` | `messages = [m.to_dict() ...]` then `format_for_show([msg])` | `format_for_show([chat_data.messages[i]])` |

## Implementation Steps

### Phase 1: ChatListEntry

1. **Define `ChatListEntry` dataclass** in `domain/chat.py`. Frozen, slotted, 6 fields matching the current dict shape.

2. **Update `chat/files.py:list_chats()`** to construct and return `list[ChatListEntry]`. Update the sort lambda to use attribute access.

3. **Update consumers** — `formatting/chat_list.py:format_chat_list_item()`, `ui/chat_ui.py:format_chat_info()`, and `ui/chat_ui.py:prompt_chat_selection()` to accept `ChatListEntry` and use attribute access. Update tests if any exist.

### Phase 2: load_profile() → RuntimeProfile

4. **Change `profile.load_profile()`** to call `RuntimeProfile.from_dict()` at the end and return `RuntimeProfile`. The function currently enriches the raw dict (maps paths, sets defaults) then returns it — `from_dict()` is compatible with the enriched dict shape. Update type annotation.

5. **Update `cli.py`** — change `profile_data` type to `RuntimeProfile`, convert all `profile_data["key"]` → `profile_data.key` and `profile_data.get("key", default)` → `getattr(profile_data, "key", default)` or direct attribute access (RuntimeProfile fields have defaults where appropriate). Note: `profile_data.get("models", {}).get(...)` patterns need special handling.

6. **Update `prompts/system_prompt.py:load_system_prompt()`** — change `profile_data: dict[str, Any]` → `profile_data: RuntimeProfile`. Replace `profile_data.get("system_prompt")` → `profile_data.system_prompt`.

7. **Update `session_manager.py:load_system_prompt()`** static method — change parameter type to `RuntimeProfile`. This just delegates to `system_prompt.load_system_prompt()`.

8. **Update `repl/loop.py`** — change `profile_data: dict` → `profile_data: RuntimeProfile` in both `print_startup_banner()` and `repl_loop()`. Convert dict-key access to attribute access. `SessionManager(profile=profile_data, ...)` already accepts `RuntimeProfile`.

### Phase 3: Fix stale dict annotations

9. **Fix `commands/context.py:HelperAIInvoker`** — change `profile: dict[str, Any]` → `profile: RuntimeProfile` in the protocol's `__call__` signature.

10. **Fix `commands/meta_generation.py`** — change `_invoke_helper_ai` parameter `profile_data: dict` → `profile_data: RuntimeProfile`.

11. **Fix `ai/runtime.py:send_message_to_ai`** — change `profile: Optional[dict] = None` → `profile: RuntimeProfile | None = None`.

### Phase 4: Formatting functions → ChatMessage

12. **Update `formatting/history.py`** — import `ChatMessage`, change all `msg: dict` parameters to `msg: ChatMessage`. Replace `.get("field", default)` → attribute access (e.g., `msg.role`, `msg.content`, `msg.hex_id or DISPLAY_MISSING_HEX_ID`). `ChatMessage.content` is always `list[str]`, simplifying content handling. Update the `list[dict]` parameters in `format_for_*()` functions to `list[ChatMessage]`.

13. **Update `formatting/text.py:format_messages`** — change `messages: list[dict]` → `messages: list[ChatMessage]` and `message_formatter: Callable[[dict], str]` → `Callable[[ChatMessage], str]`. Import `ChatMessage`.

14. **Update `meta_generation.py` callers** — for `format_for_ai_context`: use `chat_data.messages` instead of `get_messages_for_ai(chat_data)`. For `format_for_safety_check`: use `ChatMessage` objects directly instead of `[m.to_dict() for m in messages]`.

15. **Update `meta_inspection.py` callers** — for `show_history`: pass `chat_data.messages` directly to `format_messages()` instead of `[m.to_dict() for m in ...]`. For `show_message`: use `ChatMessage` attribute access and pass `ChatMessage` to `format_for_show()`. The `hex_id.get_message_index()` call currently needs a dict list — either update it to accept `ChatMessage` or keep the conversion for that one call.

### Phase 5: KeyConfig TypedDict

16. **Define `KeyConfig` TypedDict** in `keys/loader.py`. Change `load_api_key` parameter from `dict[str, Any]` to `KeyConfig`. Update `RuntimeProfile.api_keys` type from `dict[str, dict[str, Any]]` to `dict[str, KeyConfig]`. Update `profile.py` and `domain/profile.py` accordingly.

### Phase 6: Cleanup and verification

17. **Run ruff** — fix any unused imports (`Any`, `dict` from typing) or new lint issues.

18. **Run full test suite** — verify all 586+ tests pass. Fix any test files that construct raw dicts where typed models are now expected.

## Open Questions

1. **`hex_id.get_message_index()` accepts `list[dict[str, Any]] | dict[int, str]`** — should it also accept `list[ChatMessage]`? This would avoid a `to_dict()` conversion in `meta_inspection.py:show_message`. The function only accesses `msg.get("hex_id")` — easy to adapt, but expands scope.

2. **`logging/events.py:estimate_message_chars(messages: list[dict])`** — this is called from `ai/runtime.py` with provider-bound serialized messages. It's at the provider boundary. Should it stay as `dict`? (Recommendation: yes, leave it.)

3. **`profile.create_profile() -> tuple[dict[str, Any], list[str]]`** — the dict is serialized to JSON on disk. Should it return `RuntimeProfile` and serialize separately? (Recommendation: no, the dict is the serialization output.)

4. **`setup_wizard._build_profile() -> dict`** — same as above, builds JSON to write to disk. (Recommendation: leave as dict.)

5. **Should `RuntimeProfile.api_keys` be `dict[str, KeyConfig]` or stay `dict[str, dict[str, Any]]`?** — `KeyConfig` is a discriminated union by `type` field. A TypedDict with `total=False` works but loses the discriminated union constraint. A union of TypedDicts (one per type) would be precise but verbose. If the stretch goal (Phase 5) is skipped, `dict[str, dict[str, Any]]` is acceptable since the config comes from JSON and is consumed in one function.
