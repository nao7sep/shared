# PolyChat Code Review & Refactoring Plan

**Agent:** copilot
**Date:** 2026-02-11
**Scope:** Full source code review of `src/polychat/` (~347 KB across 50 files)

---

## Overall Assessment

PolyChat is a well-structured CLI chat application with good separation of concerns for its size. Architecture follows a layered pattern: CLI → REPL → Orchestrator → Providers, with SessionManager as the single source of truth. File sizes are mostly in the healthy 1–15 KB range.

The codebase is **shippable now** — nothing below is a blocking issue. The items are ordered by impact: bugs and data-loss risks first, then maintainability improvements.

---

## 1. BUGS & DATA-LOSS RISKS

### 1.1 `repl.py` — Stale closure over `chat_path` / `chat_data` in `execute_send_action`

**Severity:** High (potential data loss / wrong-file writes)
**File:** `repl.py` lines 166–354

The inner function `execute_send_action(action)` captures `chat_path` and `chat_data` from the enclosing `repl_loop` scope. However, the REPL main loop reassigns these local variables when handling `ContinueAction` (lines 407–411). The problem: `execute_send_action` references the *closure variable*, not the action's own `chat_path`/`chat_data`. If a command changes `chat_path` before `execute_send_action` runs (or during concurrent citation enrichment), the closure sees the **new** values, not the ones that were active when the user typed the message.

Inside `execute_send_action`, lines 175–178 use `chat_path` and `chat_data` from the closure rather than from `action.chat_path`/`action.chat_data`:

```python
provider_instance, error = validate_and_get_provider(
    manager,
    chat_path=chat_path,     # ← closure variable, not action's
    search=use_search,
    thinking=use_thinking,
)
```

And rollback on line 182 also passes `chat_data` from closure.

**Fix:** Derive effective `chat_path` and `chat_data` from the action first, falling back to the closure only as a default:

```python
effective_path = action.chat_path if action.chat_path is not None else chat_path
effective_data = action.chat_data if action.chat_data is not None else chat_data
```

Then use `effective_path`/`effective_data` consistently throughout `execute_send_action`.

### 1.2 `orchestrator.py` — Double hex-ID release in `handle_ai_error`

**Severity:** Medium (logic error, currently benign because `discard` is idempotent)
**File:** `orchestrator.py` lines 591–616

In `handle_ai_error`, when `mode == "normal"`, the code releases `assistant_hex_id` at line 593, then falls through to release it again at line 615. The `set.discard` is idempotent so there's no crash, but it signals confused control flow.

**Fix:** Add `return` after the normal-mode block, or guard the second release with `elif mode in ("retry", "secret")`.

### 1.3 `chat.py` — `save_chat` mutates `data["metadata"]` in-place

**Severity:** Medium (side effect on caller's dict)
**File:** `chat.py` lines 111–141

`save_chat` writes `updated_at` and `created_at` directly into the passed `data` dict (lines 122–126) before `deepcopy`-ing for persistence (line 134). The caller's in-memory chat object is permanently mutated. This is probably intentional, but if any caller relies on `updated_at` not changing after a save, they'll get a surprise.

**Recommendation:** Document this as intentional in-place mutation, or move the timestamp update into the deepcopy.

### 1.4 `chat_manager.py` — `generate_chat_filename` infinite loop potential

**Severity:** Low (practically unreachable)
**File:** `chat_manager.py` lines 66–97

The counter loop has no upper bound. In theory, if the chats directory were unwritable and the path "exists" check always returned true, this would loop forever.

**Fix:** Add a `max_counter` guard (e.g., 1000) and raise an error if exhausted.

---

## 2. POTENTIAL BUGS / EDGE CASES

### 2.1 `repl.py` — `execute_send_action` citation enrichment may leak tasks on error

**File:** `repl.py` lines 249–277

When the grace timeout fires and the second `wait_for` also times out, `enrich_task.cancel()` is called. But on the "generic `except Exception`" path (line 277), the task is NOT cancelled. This leaks background HTTP tasks.

**Fix:** Add `enrich_task.cancel()` in the outer `except Exception` handler.

### 2.2 `ai_runtime.py` — `validate_and_get_provider` accepts `SessionState` but gets `SessionManager`

**File:** `ai_runtime.py` line 176 type hint says `SessionState`, but callers always pass `SessionManager` (e.g., `repl.py` line 174). This works at runtime because both expose `.current_ai`, `.profile`, etc., but it's a type mismatch that could mislead future contributors.

**Fix:** Change the type hint to accept either `SessionState` or `SessionManager` (or use a Protocol).

### 2.3 `commands/runtime.py` — `purge_messages` doesn't clean up hex IDs

**File:** `commands/runtime.py` lines 596–648

When messages are purged via `del messages[msg_index]`, the hex IDs of deleted messages are NOT removed from `session.hex_id_set`. This means those hex IDs become phantom entries and can never be reused. Over very long sessions this is harmless, but it's an inconsistency compared to `pop_message` which does clean up.

**Fix:** Call `self.manager.remove_message_hex_id(msg_index)` before `del messages[msg_index]`, or use `self.manager.pop_message(msg_index)`.

### 2.4 `commands/runtime.py` — `rewind_messages` doesn't clean up hex IDs for bulk-deleted messages

**File:** `commands/runtime.py` line 587

`delete_message_and_following` slices the list (`data["messages"] = messages[:index]`), but the hex IDs of deleted messages are not removed from `hex_id_set`. Similar to 2.3.

**Fix:** Loop through the removed messages and call `self.manager.remove_message_hex_id()` or discard from `hex_id_set` before the deletion.

### 2.5 `claude_provider.py` — Missing `max_tokens` default for Claude

**File:** `claude_provider.py` lines 158–164

Claude API requires `max_tokens` in most cases. When `max_output_tokens` is `None` (not configured in `ai_limits`), no `max_tokens` is sent. This may cause Anthropic API to use a very low default or error depending on the model.

**Recommendation:** Consider setting a sensible default (e.g., 4096 or 8192) when no limit is configured.

---

## 3. ARCHITECTURE & SEPARATION OF CONCERNS

### 3.1 `repl.py` `execute_send_action` — Too much responsibility

**Severity:** Maintainability concern
**File:** `repl.py` lines 166–354

This ~190-line inner function handles: provider validation, streaming display, thought callbacks, citation enrichment (with two-stage timeout), logging, and response persistence. It's the thickest code in the project and mixes UI (print), network I/O (citations), and data persistence (orchestrator calls).

**Recommendation:** Extract a `SendExecutor` class or top-level async function with clear inputs/outputs. This function should:
1. Accept all needed context as parameters (no closure captures)
2. Return a result that the REPL loop acts on
3. Move citation enrichment into a helper function

This is the single highest-ROI refactoring for testability. Currently this code path is essentially untestable without running the full REPL.

### 3.2 Provider implementations — Heavy boilerplate duplication

**Files:** All 7 provider files (`openai_provider.py`, `claude_provider.py`, etc.)

Every provider re-implements:
- `format_messages` (identical in 5 of 7 providers)
- Error handling `try/except` blocks (nearly identical structure)
- `_mark_search_executed` / `_emit_thought` static methods (copied in 3+ providers)

**Recommendation:** Move shared implementations to a base class:
- `BaseProvider` with default `format_messages` (join lines to text)
- `_emit_thought` and `_mark_search_executed` as base class methods
- A shared error-logging decorator or context manager

This doesn't need to be a full abstract class — just a mixin with shared utilities. The OpenAI-compatible providers (Grok, Perplexity, Mistral, DeepSeek) share even more code and could potentially share a common `OpenAICompatibleProvider` base.

**Impact:** ~200–300 lines of duplicated code removed, and new providers become easier to add.

### 3.3 `session_manager.py` — Growing responsibility

**File:** `session_manager.py` (26 KB, largest file)

SessionManager manages: AI state, chat state, retry mode, secret mode, hex IDs, provider caching, timeouts, system prompts, and persistence. It's the "god object" risk.

**Recommendation (future):** This is acceptable for current project size. If SessionManager grows further, consider extracting:
- Retry/secret mode management → `ModeManager`
- Provider caching → already partially in `SessionState`

No immediate action needed — just be aware of the trend.

---

## 4. CORRECTNESS / ROBUSTNESS

### 4.1 `logging_utils.py` — `log_event` timestamp is redundant with formatter

**File:** `logging_utils.py` line 374

`log_event` injects `"ts"` into the payload, but `StructuredTextFormatter.format()` also generates `"ts"` in `base` dict (line 263). The formatter's `"ts"` then gets overwritten by the payload's `"ts"` via `base.update(parsed)`. This means the formatter-generated timestamp is always discarded.

**Fix:** Remove `"ts"` from `log_event` and let the formatter handle it, OR remove the formatter's `"ts"` generation. Having both is confusing.

### 4.2 `html_parser.py` — `_NUMERIC_TITLE_RE` defined twice

**File:** `citations.py` line 15 and `html_parser.py` line 16

Same regex `^\s*\d+\s*$` is defined in both modules. Minor duplication.

**Fix:** Import from one location.

### 4.3 `profile.py` — `map_path` doesn't normalize paths

**File:** `profile.py` line 66

`Path(path).is_absolute()` followed by `str(Path(path))` doesn't resolve symlinks or normalize `..` components. A path like `/Users/nao7sep/../nao7sep/code` would be accepted as-is.

**Recommendation:** Use `Path(path).resolve()` for absolute paths to canonicalize. Low priority since users rarely pass non-normalized absolute paths.

---

## 5. MINOR IMPROVEMENTS (Do if touching these files anyway)

### 5.1 `models.py` — `candidates` variable shadowed

**File:** `models.py` line 143

```python
candidates: List[str] = []
```

This re-declares `candidates` with a type annotation inside an `else` block, shadowing the parameter-based assignment on line 141. Works, but some linters/type checkers may warn.

### 5.2 `commands/metadata.py` — `content` field may be a list, not str

**File:** `commands/metadata.py` line 88

```python
f"{msg['role']}: {msg.get('content', '')[:200]}"
```

`content` is `list[str]` in PolyChat format. Slicing a list gives a list, not a truncated string. Should use `self._message_content_to_text(msg.get('content', ''))[:200]`.

### 5.3 `commands/metadata.py` — Summary context may exceed token limits

**File:** `commands/metadata.py` line 171

For `generate_summary`, the full message history is concatenated as context. For very long chats, this could exceed the helper AI's context window.

**Recommendation:** Add a character/message limit (e.g., last 50 messages or 50K chars).

---

## 6. NOT RECOMMENDED (Mentioned for completeness, but low ROI)

- **Type-checking strictness** — `mypy` is set to `disallow_untyped_defs = false`. Enabling this would require many type annotations but offers limited bug-finding benefit for this codebase size.
- **Provider factory pattern** — Replacing `PROVIDER_CLASSES` dict with an abstract factory. Current dict lookup is simple and clear.
- **Dataclass for profile** — Replacing `dict[str, Any]` with a typed dataclass. High churn, moderate benefit.

---

## Priority Order for Implementation

| Priority | Item | Impact | Effort |
|----------|------|--------|--------|
| P0 | 1.1 Stale closure in `execute_send_action` | Prevents wrong-file writes | Small |
| P0 | 2.3 + 2.4 Hex ID cleanup in purge/rewind | Data consistency | Small |
| P1 | 1.2 Double hex-ID release | Code clarity | Tiny |
| P1 | 2.1 Citation task leak | Resource cleanup | Tiny |
| P1 | 5.2 Content list truncation bug | Correct display | Tiny |
| P2 | 3.1 Extract send execution from REPL | Testability | Medium |
| P2 | 3.2 Provider base class | Maintainability, ~200 LOC saved | Medium |
| P2 | 2.2 Type hint mismatch | Developer clarity | Tiny |
| P3 | 4.1 Redundant timestamp | Code clarity | Tiny |
| P3 | 5.3 Summary context limit | Robustness | Small |
| P3 | 2.5 Claude default max_tokens | API robustness | Small |

---

## Summary

The codebase is in good shape for its maturity stage. The highest-impact items are:

1. **Fix the stale closure bug** in `repl.py`'s `execute_send_action` (P0, prevents potential data-loss)
2. **Fix hex ID leaks** in purge/rewind commands (P0, data consistency)
3. **Extract send execution** from the REPL loop (P2, biggest testability win)
4. **DRY up provider implementations** with a base class (P2, biggest maintainability win)

Items 1–2 are surgical fixes (a few lines each). Items 3–4 are larger refactors that should be done when the team has bandwidth, not as blockers to shipping.
