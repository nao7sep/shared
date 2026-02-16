# PolyChat Code Review and Safe-Shipping Refactor Plan (Codex, 2026-02-11)

## Context
- Goal alignment:
  - Primary: ship safe code fast.
  - Secondary: improve separation of concerns without over-engineering.
  - No micro-optimization work.
- Review scope completed:
  - Source modules under `src/polychat/`
  - Test suite and quality checks:
    - `poetry run pytest -q` (439 passed, 3 deselected)
    - `poetry run mypy src` (311 errors)
    - `poetry run ruff check src tests` (test lint issues)

## Findings Driving This Plan
1. Confirmed runtime bug in `/purge` when no chat is open:
   - `src/polychat/commands/runtime.py` directly indexes `chat["messages"]` without open-chat guard.
   - Repro: instantiate `SessionManager(chat=None)` then call `purge_messages("abc")` -> `KeyError: 'messages'`.
2. Helper AI metadata commands build low-quality/unbounded prompts:
   - `generate_title` and `generate_summary` serialize message `content` lists directly and summary sends the full history unbounded.
   - This increases failure/cost risk on long chats and degrades title/summary quality.
3. Type-safety debt is high and currently not actionable in CI:
   - 311 `mypy` errors across runtime/provider/command boundaries.
   - Raw dict state and mixin attribute assumptions are causing brittle contracts.
4. Separation of concerns is workable but imbalanced in high-risk modules:
   - `repl.py` and `commands/runtime.py` combine UI interaction, orchestration, domain mutation, and persistence.
   - This increases regression risk for future feature work.

## Execution Strategy (Safe Shipping First)

### Phase 1: Immediate Safety Hotfixes (same release)
Purpose: remove known crash conditions and reduce production support risk.

1. Fix `/purge` precondition handling.
- Change:
  - Add `_require_open_chat(need_messages=True)` guard in `purge_messages`.
  - Return user-facing message (`"No chat is currently open"`) instead of raising `KeyError`.
- Tests:
  - Add test for `/purge` with no active chat.
- Acceptance:
  - No unhandled exception path when `/purge` is called without an open chat.

2. Normalize content-to-text usage in title/summary prompt assembly.
- Change:
  - Use `_message_content_to_text()` when building helper prompt context.
  - Ensure deterministic line joining for list content.
- Tests:
  - Add tests with multi-line list content for title/summary generation prompt building.
- Acceptance:
  - No Python-list string artifacts in helper prompt payloads.

3. Add bounded context policy for `/summary` generation.
- Change:
  - Introduce message/window cap (configurable constant) for summary generation.
  - Include explicit truncation note in prompt when context is clipped.
- Tests:
  - Add test with oversized history verifying cap behavior.
- Acceptance:
  - Summary helper call remains bounded and predictable on long chats.

### Phase 2: High-ROI Maintainability Improvements (next release)
Purpose: reduce bug surface and make future changes safer/faster.

4. Introduce typed chat/session contracts at mutation boundaries.
- Change:
  - Add `TypedDict` (or lightweight dataclass wrappers) for chat metadata/message structures.
  - Validate command-entry mutation paths (`rewind`, `purge`, metadata updates).
- Tests:
  - Expand command tests for malformed chat/message payloads.
- Acceptance:
  - Mutation commands fail gracefully with user-facing errors instead of key/index exceptions.

5. Reduce `repl.py` responsibility by extracting AI request execution.
- Change:
  - Move provider invocation + citation enrichment + response logging into a dedicated service module.
  - Keep REPL focused on input loop and action dispatch.
- Tests:
  - Unit test service module with mocked provider streams and metadata.
- Acceptance:
  - `repl.py` complexity reduced; behavior parity maintained via tests.

6. Stabilize command-layer separation between interaction and domain updates.
- Change:
  - Standardize command handlers to avoid direct `print()` calls; route via interaction/output abstraction.
  - Keep state mutations in dedicated helpers.
- Tests:
  - Update command tests to validate returned outputs/signals instead of side effects.
- Acceptance:
  - Command behavior becomes easier to test and reason about without terminal coupling.

### Phase 3: Quality Gate Hardening (incremental, non-blocking initially)
Purpose: prevent recurrence while preserving release velocity.

7. Establish a mypy baseline file and burn-down plan.
- Change:
  - Freeze current mypy output as baseline, fail CI only on regressions.
  - Prioritize burn-down in core modules first (`commands/runtime.py`, `repl.py`, `ai_runtime.py`).
- Acceptance:
  - No new type errors introduced while gradually reducing total count.

8. Clean test lint debt and set practical lint target.
- Change:
  - Fix current `ruff` findings in tests (unused imports/vars and trivial f-strings).
  - Keep rules focused on signal over noise.
- Acceptance:
  - `ruff check src tests` passes or has an explicit reviewed ignore policy.

## Prioritization and Stop Conditions
- Ship now after Phase 1 is complete and verified.
- Treat Phase 2 as next-release batch; do not block shipping on full architectural cleanup.
- Phase 3 can run in parallel with feature work if no regression pressure.

## Verification Checklist
- Automated:
  - `poetry run pytest -q`
  - `poetry run ruff check src tests`
  - `poetry run mypy src` (baseline-regression mode after gating setup)
- Manual:
  - `/purge` with no chat open
  - `/title` and `/summary` on multiline messages
  - `/summary` on long chat history
  - normal chat send/retry/apply/cancel flows

## Risk Notes
- Main risk is behavior drift in command UX while decoupling output pathways.
- Mitigation:
  - Keep Phase 1 tightly scoped.
  - Add focused tests before structural extraction.
  - Use small PR slices with explicit acceptance criteria per phase.
