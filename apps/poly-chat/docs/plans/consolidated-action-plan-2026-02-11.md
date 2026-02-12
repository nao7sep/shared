# PolyChat Consolidated Action Plan

**Date:** 2026-02-11
**Sources:** 4 independent code reviews (Copilot/Opus 4.6, Claude/Sonnet 4.5, Codex/GPT-5.2, Gemini 3 Pro)
**Prior work:** comprehensive-issue-remediation-plan-2026-02-10 and tangled-type-separation-plan-2026-02-10 (already implemented by Codex)

---

## Overall Assessment

All four reviews agree: **the codebase is shippable now**. No critical blocking bugs. The findings below are ordered by consensus severity and ROI.

Key consensus points:
- `repl.py`'s `execute_send_action` is too large and needs extraction (4/4 agree)
- Provider implementations have heavy boilerplate duplication (3/4)
- `session_manager.py` and `commands/runtime.py` are oversized (3/4)
- Exception handling is too shallow in key paths (3/4)
- Hex ID management has consistency gaps (2/4)

---

## Tier 1: Bugs & Data-Loss Risks

Fix these first. Small, surgical changes.

### 1.1 Stale closure over `chat_path`/`chat_data` in `execute_send_action`

**Consensus:** Copilot (P0). Unique finding — highest severity item.
**Risk:** Wrong-file writes when closure variables are reassigned by REPL loop.
**Fix:** Derive `effective_path`/`effective_data` from the action, falling back to closure.
**Files:** `repl.py`
**Effort:** Small

### 1.2 Hex ID cleanup missing in purge/rewind

**Consensus:** Copilot (P0). Unique finding.
**Risk:** Phantom hex IDs accumulate in `hex_id_set` after message deletion.
**Fix:** Call `remove_message_hex_id()` or discard from `hex_id_set` before deletion.
**Files:** `commands/runtime.py`
**Effort:** Small

### 1.3 `/purge` crash when no chat is open

**Consensus:** Codex (Phase 1). Unique finding — confirmed runtime bug.
**Risk:** `KeyError: 'messages'` when `/purge` called without open chat.
**Fix:** Add `_require_open_chat(need_messages=True)` guard.
**Files:** `commands/runtime.py`
**Effort:** Tiny

### 1.4 Content list treated as string in metadata commands

**Consensus:** Copilot (P1) + Codex (Phase 1).
**Risk:** `msg.get('content', '')[:200]` slices a list, not a string. Title/summary prompts get Python list artifacts.
**Fix:** Use `_message_content_to_text()` before truncation.
**Files:** `commands/metadata.py`
**Effort:** Tiny

### 1.5 Double hex-ID release in `handle_ai_error`

**Consensus:** Copilot (P1). Unique finding.
**Risk:** Logic confusion — `assistant_hex_id` released twice in normal mode. Currently benign (idempotent discard).
**Fix:** Add `return` after normal-mode block, or guard with `elif`.
**Files:** `orchestrator.py`
**Effort:** Tiny

### 1.6 Citation enrichment task leak on error

**Consensus:** Copilot (P1) + Claude (Phase 3).
**Risk:** Background HTTP tasks not cancelled on generic `except Exception` path.
**Fix:** Add `enrich_task.cancel()` in outer exception handler.
**Files:** `repl.py`
**Effort:** Tiny

---

## Tier 2: Robustness & Safety

Fix soon. Prevents production incidents and improves debuggability.

### 2.1 Shallow exception handling — add logging

**Consensus:** Claude (Phase 1, HIGH) + Copilot (mentions several).
**Problem:** Bare `except Exception: pass` in citation enrichment and elsewhere. Silent failures make debugging impossible.
**Fix:** Add `logger.exception()` with structured context to all broad catches.
**Files:** `repl.py`, `orchestrator.py`, `chat_files.py`, `commands/runtime.py`
**Effort:** 2–3 hours

### 2.2 Summary context unbounded for `/summary`

**Consensus:** Copilot (P3) + Codex (Phase 1).
**Problem:** Full message history concatenated as helper AI context. Can exceed token limits on long chats.
**Fix:** Add message/character cap with truncation note in prompt.
**Files:** `commands/metadata.py`
**Effort:** Small

### 2.3 Missing type/null validation in message processing

**Consensus:** Claude (Phase 1, HIGH) + Codex (Phase 2).
**Problem:** Chat data loaded from JSON without strict shape validation. Malformed content can propagate into providers.
**Fix:** Add `validate_message()` function and TypedDict for message structure at load boundary.
**Files:** `chat.py`
**Effort:** 2–3 hours

### 2.4 Error message sanitization gaps

**Consensus:** Claude (Phase 1, MEDIUM). Unique finding.
**Problem:** Some ValueError messages constructed from untrusted input without sanitization. API keys could leak in edge cases.
**Fix:** Wrap error construction with `sanitize_error_message()`.
**Files:** `commands/base.py`, `commands/chat_files.py`
**Effort:** 1–2 hours

### 2.5 Async citation patterns — resource leak

**Consensus:** Claude (Phase 3, HIGH) + Copilot (P1).
**Problem:** `asyncio.shield()` prevents actual cancellation on timeout. Background tasks continue consuming HTTP connections.
**Fix:** Remove `asyncio.shield()`, let timeout actually cancel. Simplify to single timeout level.
**Files:** `repl.py`
**Effort:** Small

### 2.6 Claude provider missing `max_tokens` default

**Consensus:** Copilot (P2). Unique finding.
**Problem:** When `max_output_tokens` is None, no `max_tokens` sent. May cause API errors.
**Fix:** Set sensible default (e.g., 8192) when no limit configured.
**Files:** `claude_provider.py`
**Effort:** Tiny

### 2.7 Path traversal protection incomplete

**Consensus:** Claude (Phase 3, MEDIUM).
**Problem:** `~/` and `@/` path mapping in profile doesn't validate destination stays within boundaries.
**Fix:** Add `.resolve()` + `.relative_to()` validation for all mapped paths.
**Files:** `profile.py`
**Effort:** Small

---

## Tier 3: Architecture & Maintainability

Larger refactors. Do when bandwidth allows. Highest long-term ROI.

### 3.1 Extract AI execution from `repl.py` ⭐ HIGHEST ROI

**Consensus:** All 4 reviews agree this is the #1 refactoring priority.
- Copilot: Extract `SendExecutor` class (P2)
- Claude: Extract `AIInvocationHandler` into `ai_invocation.py` (Phase 2)
- Codex: Move to dedicated service module (Phase 2)
- Gemini: Create `AIExecutionService` in `ai/service.py` (Phase 1)

**Problem:** `execute_send_action` is ~190 lines handling provider validation, streaming, thoughts, citations, logging, and persistence. Untestable without full REPL.
**Impact:** 50% reduction in REPL complexity, testable AI execution path.
**Files:** `repl.py` → new `ai_invocation.py` or `ai/service.py`
**Effort:** Medium (2–3 hours)

### 3.2 Provider base class — DRY up implementations

**Consensus:** Copilot (P2) + Codex (Phase 2, protocol alignment).
**Problem:** 5 of 7 providers duplicate `format_messages`, error handling, `_emit_thought`, `_mark_search_executed`.
**Fix:** Create `BaseProvider` with shared implementations. OpenAI-compatible providers (Grok, Perplexity, Mistral, DeepSeek) could share `OpenAICompatibleProvider`.
**Impact:** ~200–300 lines removed. New providers easier to add.
**Files:** All provider files under `ai/`
**Effort:** Medium (3–4 hours)

### 3.3 Split `commands/runtime.py`

**Consensus:** Claude (Phase 2) + Gemini (Phase 2).
**Problem:** 648 lines with 15+ command methods in one class.
**Fix:** Split into `commands/model.py`, `commands/mode.py`, `commands/status.py`.
**Files:** `commands/runtime.py` → 3 files
**Effort:** Medium (2 hours)

### 3.4 Split `session_manager.py`

**Consensus:** Claude (Phase 2) + Gemini (Phase 3) + Copilot (noted as trend).
**Problem:** 764 lines / 26 KB — manages AI state, chat state, retry, secret, hex IDs, provider caching, timeouts, system prompts, and persistence.
**Fix:** Extract `RetryModeManager`, `SecretModeManager`, and persistence helpers.
**Files:** `session_manager.py` → 2–3 files
**Effort:** Medium (2 hours)

### 3.5 Centralize UI interactions

**Consensus:** Gemini (Phase 4) + Codex (Phase 2, blocking `input()`).
**Problem:** Commands call `input()` directly within async handlers. Domain logic tangled with console I/O.
**Fix:** Expand `UserInteractionPort` abstraction. Route all console output through it.
**Files:** `commands/runtime.py`, `commands/chat_files.py`, `repl.py`
**Effort:** Medium-Large

---

## Tier 4: Quality Gates & Minor

Incremental improvements. Do if touching these files anyway.

### 4.1 mypy baseline and burn-down (Codex)
- Freeze current 311 errors as baseline, fail CI only on regressions
- Burn down in core modules first

### 4.2 Redundant timestamp in logging (Copilot)
- `log_event` injects `"ts"` that gets overwritten by formatter's `"ts"`
- Remove one

### 4.3 Duplicate regex `_NUMERIC_TITLE_RE` (Copilot)
- Defined in both `citations.py` and `html_parser.py`
- Import from one location

### 4.4 `save_chat` in-place mutation (Copilot)
- Documents as intentional, or move timestamp update into deepcopy

### 4.5 `generate_chat_filename` infinite loop guard (Copilot)
- Add `max_counter` guard (e.g., 1000)

### 4.6 Type hint: `validate_and_get_provider` accepts wrong type (Copilot)
- Hint says `SessionState`, callers pass `SessionManager`

### 4.7 Path normalization in `map_path` (Copilot)
- Use `Path.resolve()` for absolute paths

---

## Execution Order

**Phase 1 — Immediate (ship-safe):** Tier 1 items (1.1–1.6)
- All are small/tiny fixes. Do in one session.
- Run full test suite after.

**Phase 2 — Soon (robustness):** Tier 2 items (2.1–2.7)
- Focus on exception handling (2.1), validation (2.3), and async fix (2.5).
- 1–2 sessions.

**Phase 3 — Next sprint (architecture):** Tier 3 items (3.1–3.5)
- Start with 3.1 (extract AI execution) — highest consensus and ROI.
- Then 3.2 (provider base class) and 3.3 (split runtime commands).
- 3.4 and 3.5 can wait unless touching those files.

**Phase 4 — Ongoing:** Tier 4 items as opportunities arise.

---

## Items NOT Recommended (consensus: low ROI)

- Enabling strict mypy (`disallow_untyped_defs`) — high churn, limited bug-finding
- Provider factory pattern — current dict lookup is simple and clear
- Dataclass for profile — high churn, moderate benefit
- Full async lock for hex IDs — currently safe in single-threaded REPL

---

## Agreement Matrix

| Finding | Copilot | Claude | Codex | Gemini | Tier |
|---------|---------|--------|-------|--------|------|
| Stale closure in execute_send_action | ✅ P0 | | | | 1 |
| Hex ID cleanup in purge/rewind | ✅ P0 | | | | 1 |
| /purge crash no chat | | | ✅ Ph1 | | 1 |
| Content list as string | ✅ P1 | | ✅ Ph1 | | 1 |
| Citation task leak | ✅ P1 | ✅ Ph3 | | | 1 |
| Extract AI execution from REPL | ✅ P2 | ✅ Ph2 | ✅ Ph2 | ✅ Ph1 | 3 |
| Shallow exception handling | ✅ | ✅ Ph1 | | | 2 |
| Summary context unbounded | ✅ P3 | | ✅ Ph1 | | 2 |
| Message validation at load | | ✅ Ph1 | ✅ Ph2 | | 2 |
| Provider base class / DRY | ✅ P2 | | ✅ Ph2 | | 3 |
| Split session_manager.py | ✅ | ✅ Ph2 | | ✅ Ph3 | 3 |
| Split commands/runtime.py | | ✅ Ph2 | ✅ Ph2 | ✅ Ph2 | 3 |
| Async citation patterns | ✅ P1 | ✅ Ph3 | | | 2 |
| Path traversal | | ✅ Ph3 | | | 2 |
| Centralize UI interactions | | | ✅ Ph2 | ✅ Ph4 | 3 |
| Error sanitization | | ✅ Ph1 | | | 2 |
