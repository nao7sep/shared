# Code Review: Dict-to-Type Migration (843cf369)

Review of commit `843cf369b646ef3f77aac1683dd60cdb83d46359` — "Refactor tests to use Task and TaskStore models". Despite the commit message referencing Task/TaskStore (which applies to the `tk` app), the polychat-side changes are a large-scale migration from raw `dict` access to typed domain models (`RuntimeProfile`, `ChatDocument`, `ChatMessage`, `ChatListEntry`, `RetryAttempt`).

## Summary

The commit replaces `dict[str, Any]` signatures and `data["key"]` / `data.get("key")` access patterns with typed dataclass attribute access across ~40 source files. New dataclasses `ChatListEntry` and `RetryAttempt` are introduced in `domain/chat.py`. The `SessionManager` dict-like API (`__getitem__`, `__setitem__`, `.get()`) and its backing helpers (`state_getitem`, `state_setitem`, `state_get`) are removed. `profile.load_profile()` now returns `RuntimeProfile` directly instead of round-tripping through `.to_dict()`.

This is a significant structural improvement aligned with the PLAYBOOK's data-modeling rule ("Never use raw dicts for structured data").

---

## Findings

### 1. Correctness — `_require_open_chat` lost its guard semantics

**File:** `src/polychat/commands/base.py`, lines 47–58

**Before:** The function returned `None` when `chat_data` was falsy, was not a dict, or was missing `"messages"` / `"metadata"` keys. This was a strict gate.

**After:**
```python
chat_data = self.manager.chat
if not chat_data.messages and not chat_data.metadata.title and not chat_data.metadata.created_utc:
    if need_messages or need_metadata:
        if not self.manager.chat_path:
            return None
return chat_data
```

`self.manager.chat` now always returns a `ChatDocument` (never `None`), so the notion of "no chat open" is approximated by checking emptiness heuristics. However:

- When `need_messages=False` and `need_metadata=False` (the default), the function **always returns** a `ChatDocument`, even when no chat is open. Previously it would return `None` for an empty/falsy dict. Any caller that checks `if chat_data is None` after calling `_require_open_chat()` without keyword arguments will now silently receive an empty document. Verify that no caller relies on `None` from `_require_open_chat()` with defaults to detect "no chat open".
- When a chat file exists but has zero messages and no title/created_utc, but `chat_path` is set, the function returns the data — this is correct. But the three-field emptiness heuristic (`messages`, `title`, `created_utc`) is fragile: a chat with only a `summary` or `system_prompt` in metadata would also pass through as "empty" if it has no messages. Consider whether `ChatDocument` should expose an `.is_empty()` predicate to consolidate this logic.

**Severity:** Medium. The behavioral change for default arguments is subtle and may cause unexpected pass-through of empty documents.

---

### 2. Correctness — `getattr` used where direct attribute access is safe

**File:** `src/polychat/commands/meta_inspection.py`, lines 183–199

```python
system_prompt_display = getattr(profile_data, "system_prompt", None) or DISPLAY_NONE
title_prompt = getattr(profile_data, "title_prompt", None) or DISPLAY_NONE
summary_prompt = getattr(profile_data, "summary_prompt", None) or DISPLAY_NONE
safety_prompt = getattr(profile_data, "safety_prompt", None) or DISPLAY_NONE
...
f"Chats:     {getattr(profile_data, 'chats_dir', DISPLAY_UNKNOWN)}",
f"Logs:      {getattr(profile_data, 'logs_dir', DISPLAY_UNKNOWN)}",
```

`profile_data` is `RuntimeProfile`, a `@dataclass(slots=True)` — all these fields are always present. Using `getattr` with a fallback hides any future attribute rename at the type-checking level. Direct attribute access (`profile_data.system_prompt`) is already used elsewhere in this same commit (e.g., `meta_generation.py` line 83). This inconsistency suggests the `getattr` calls were a cautious leftover rather than intentional.

**Severity:** Low. Not a runtime bug, but defeats static type checking for these accesses. A follow-up cleanup should replace them with direct attribute access to match the rest of the migration.

---

### 3. Correctness — `hex_id.build_hex_map` / `get_message_index` / `get_hex_id` lose type safety

**File:** `src/polychat/hex_id.py`, lines 96–134

Signatures changed from `list[dict[str, Any]]` to bare `list`. The body now uses `getattr(message, "hex_id", None)` instead of `message.get("hex_id")`.

Using bare `list` and `getattr` makes these functions accept any iterable of any object. This is a step backward from the commit's goal: since every caller now passes `list[ChatMessage]`, the signatures should be `list[ChatMessage]` (or a protocol with `hex_id: str | None`). The `getattr` fallback will silently return `None` for objects that are not `ChatMessage`, masking type errors.

**Severity:** Low. Functions work correctly in practice; the type annotations are weaker than they could be.

---

### 4. Correctness — `format_for_ai_context` now receives `list[ChatMessage]` but `generate_title`/`generate_summary` previously filtered error messages

**File:** `src/polychat/commands/meta_generation.py`, lines 73–76 and 131–134

**Before:**
```python
messages = get_messages_for_ai(chat_data)   # filtered out error messages
context_text = format_for_ai_context(messages)
```

**After:**
```python
if not chat_data.messages:
    return "No messages in chat to generate title from"
context_text = format_for_ai_context(chat_data.messages)  # ALL messages, including errors
```

The `get_messages_for_ai()` call was removed and replaced with `chat_data.messages` directly. This means error messages are now included in the context sent to the helper AI for title/summary generation. This is a behavioral change — error messages (which contain stack traces, provider errors, etc.) will pollute the title/summary generation context.

**Severity:** Medium. Error messages will be sent to the helper AI as context for title/summary generation, producing lower-quality or confusing results.

---

### 5. Correctness — `save_chat` change-detection compares dict vs. ChatDocument internals

**File:** `src/polychat/chat/storage.py`, lines 68–84

The save path does `data.to_dict()` → compare with `_load_existing_persistable_chat()` which returns a raw `dict`. If unchanged, it reconstructs `ChatMetadata.from_raw(existing_metadata_raw)` to sync timestamps. This works, but the no-change path does an extra `ChatMetadata.from_raw()` parse on every save that detects no change. This is not a bug but is worth noting as a minor inefficiency introduced by the mixed dict/object boundary in this function.

**Severity:** Negligible.

---

### 6. Correctness — `resolve_profile_timeout` dual-dispatch on type

**File:** `src/polychat/timeouts.py`, lines 69–73

```python
def resolve_profile_timeout(profile: RuntimeProfile | Mapping[str, Any] | None) -> int | float:
    if isinstance(profile, RuntimeProfile):
        raw_timeout = profile.timeout
    elif isinstance(profile, Mapping):
        raw_timeout = profile.get("timeout")
```

The function now accepts both `RuntimeProfile` and `Mapping`. Given that the entire commit is about removing dict access, retaining the `Mapping` branch suggests incomplete migration (possibly kept for test compatibility). If the `Mapping` branch is no longer reachable from production code, it should be removed to avoid dead code.

**Severity:** Low. Dead code path if migration is complete; not a bug.

---

### 7. Correctness — redundant `messages` re-assignment in `purge_messages`

**File:** `src/polychat/commands/runtime_mutation.py`, lines 97 and 121

```python
messages = chat_data.messages     # line 97, after _require_open_chat
...
messages = chat_data.messages     # line 121, added in this commit
for msg_index, _hid in indices_to_delete:
    ...
    del messages[msg_index]
```

The re-assignment at line 121 is harmless (both point to the same list object since `ChatDocument.messages` is a plain `list` attribute), but it is unnecessary and suggests confusion about whether the reference might have gone stale. Can be cleaned up.

**Severity:** Negligible.

---

## Verdict

The migration is well-executed mechanically — hundreds of `data["key"]` → `data.key` conversions applied consistently. Finding **#4** (error messages leaking into title/summary generation) is the most impactful behavioral regression and should be addressed. Finding **#1** (`_require_open_chat` guard semantics change) deserves verification that no caller depends on `None` with default arguments. The remaining findings are low-severity cleanup items.
