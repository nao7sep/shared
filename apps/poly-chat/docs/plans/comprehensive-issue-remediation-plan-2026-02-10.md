# PolyChat Comprehensive Issue Remediation Plan (2026-02-10)

Status: Proposed
Audience: AI coding agents implementing stabilization and high-ROI refactors
Primary goal: Ship safe code fast
Secondary goal: Improve maintainability with balanced separation of concerns

## 1. Product/Engineering Constraints (must follow)

1. No micro-optimization work.
2. Every refactor must have a concrete purpose: bug reduction, significant reliability/perf gain, improved testability/maintainability, or clearer ownership boundaries.
3. Time to market is priority #1. Code quality is #2.
4. Separation of concerns should be balanced, not over-engineered.
5. Prefer small/medium source files and focused responsibilities.

## 2. Current Baseline and Blocking Facts

1. Manual full-code review completed across `src/poly_chat` and tests.
2. Full automated test run was not executable in this environment, but parse-level verification was run via:
   - `python3 -m compileall -q src tests`
3. Parse check currently fails due syntax error in tests:
   - `tests/test_orchestrator.py:15`
4. Known runtime correctness bugs and design issues are cataloged below with file/line evidence.

## 3. Severity Summary

P0 (must fix first, release blockers):
1. Unknown model/helper commands crash because of stale state reference.
2. Provider validation failure can leave unsent user messages in session/chat state.
3. Test suite parse failure (syntax error).

P1 (high ROI correctness + robustness):
1. Profile tests out of sync with required schema (`pages_dir`).
2. Chat schema validation too weak at load boundary; malformed content can propagate into providers.
3. Windows path handling bug in chat rename path classification.
4. Search/thinking mode flags can become inconsistent after provider/model switch.
5. Citation-page filename collision risk (possible overwrite).

P2 (maintainability/architecture hardening):
1. Async command layer uses blocking console I/O (`input()`), tangling UI and domain logic.
2. Provider protocol signature drift (`AIProvider` vs implementations/runtime usage).
3. Test imports mix `poly_chat` and `src.poly_chat` namespaces, risking duplicate module state and flaky patching.

## 4. Detailed Issue Catalog and Fix Plan

### P0-01: Unknown model/helper command crash

Problem:
1. `set_model` and `set_helper` use `self.session` (non-existent in current architecture), causing `AttributeError` for unknown model names.

Evidence:
1. `src/poly_chat/commands/runtime.py:45`
2. `src/poly_chat/commands/runtime.py:82`

Root cause:
1. Migration from dict-based session to `SessionManager` left stale references.

Implementation steps:
1. Replace stale references with `self.manager.current_ai` / `self.manager.helper_ai`.
2. Keep behavior that allows unknown model names (for newly released models).
3. Ensure return messages remain user-friendly and deterministic.

Files to edit:
1. `src/poly_chat/commands/runtime.py`

Tests to add/update:
1. Add tests for unknown `/model <name>` and `/helper <name>` to ensure no crash and correct provider display.
2. Suggested file: `tests/test_commands_runtime.py`.

Acceptance criteria:
1. `/model foo-new-model` does not crash.
2. `/helper foo-new-model` does not crash.
3. Behavior covered by unit tests.

---

### P0-02: Phantom unsent user message when provider validation fails

Problem:
1. In normal mode, user message is appended before provider validation/send.
2. If provider validation fails, function returns early and message is not rolled back.
3. This can leave unsent input in session state and later AI context.

Evidence:
1. Message appended before send: `src/poly_chat/orchestrator.py:497`
2. Validation error early return: `src/poly_chat/repl.py:157`

Root cause:
1. Send path assumes validation happens after safe state transitions; rollback path exists for streaming errors, not pre-send validation errors.

Implementation options (pick one; option A preferred for speed):
1. Option A (recommended): in REPL validation-error branch, rollback last pending user message for normal mode and persist.
2. Option B: refactor orchestration so user message is only committed after successful provider validation.

Implementation details for option A:
1. Add dedicated orchestrator method (or helper) for pre-send failure rollback in normal mode.
2. Reuse existing pop/save behavior used by cancel/error handlers, but with correct user-visible message.
3. Ensure retry/secret modes are untouched.

Files to edit:
1. `src/poly_chat/repl.py`
2. `src/poly_chat/orchestrator.py`
3. Possibly `src/poly_chat/session_manager.py` (only if helper API needed)

Tests to add/update:
1. New orchestrator/REPL test: provider validation failure leaves no extra user message.
2. Suggested files: `tests/test_orchestrator.py` and/or `tests/test_repl_orchestration.py`.

Acceptance criteria:
1. After provider validation failure, chat message count is unchanged from pre-input state.
2. No unsent user message is persisted or reused as context.

---

### P0-03: Test suite syntax error

Problem:
1. `tests/test_orchestrator.py` has invalid call syntax.

Evidence:
1. `tests/test_orchestrator.py:15`

Implementation steps:
1. Fix fixture construction syntax.
2. Re-run parse-level check.

Files to edit:
1. `tests/test_orchestrator.py`

Acceptance criteria:
1. `python3 -m compileall -q src tests` passes.

---

### P1-01: Profile tests out of sync with required schema

Problem:
1. `validate_profile` requires `pages_dir`.
2. Some tests constructing valid profile fixtures omit it.

Evidence:
1. Required fields include `pages_dir`: `src/poly_chat/profile.py:131`
2. Example missing `pages_dir`: `tests/test_profile.py:165`

Implementation steps:
1. Update profile tests to include `pages_dir` wherever profile is expected valid.
2. Keep strict schema requirement unchanged unless product decision changes.

Files to edit:
1. `tests/test_profile.py`

Acceptance criteria:
1. Profile tests match current schema contract.
2. No false-negative test failures due fixture drift.

---

### P1-02: Weak chat load validation and normalization

Problem:
1. `load_chat` only checks key presence, not data shape.
2. Provider formatters assume message `content` is `list[str]`.
3. Malformed/legacy data can produce corrupted content or runtime errors.

Evidence:
1. Weak check: `src/poly_chat/chat.py:49`
2. Formatter assumption (`lines_to_text` called on `msg["content"]`):
   - `src/poly_chat/ai/openai_provider.py:72`
   - `src/poly_chat/ai/claude_provider.py:69`
   - `src/poly_chat/ai/gemini_provider.py:64`
   - `src/poly_chat/ai/grok_provider.py:71`
   - `src/poly_chat/ai/perplexity_provider.py:90`
   - `src/poly_chat/ai/mistral_provider.py:72`
   - `src/poly_chat/ai/deepseek_provider.py:72`

Implementation steps:
1. Add explicit schema validation/normalization at load boundary.
2. Normalize message content safely:
   - If string, convert with `text_to_lines`.
   - If list, cast entries to string (or reject non-strings explicitly).
   - If unsupported type, raise `ValueError`.
3. Validate `metadata` as dict and ensure required metadata keys exist (default to `None` when absent).
4. Keep backward compatibility for benign legacy files where possible.

Files to edit:
1. `src/poly_chat/chat.py`
2. Possibly `src/poly_chat/message_formatter.py` (if helper normalization needed)

Tests to add/update:
1. `load_chat` with string content should normalize to list-of-lines.
2. Invalid `messages`/`metadata` types should raise clear error.
3. Existing valid chat fixtures remain accepted.

Acceptance criteria:
1. Providers receive normalized message shape consistently.
2. Malformed file errors are deterministic and user-actionable.

---

### P1-03: Windows path handling bug in rename

Problem:
1. `rename_chat` uses `"/" in new_name` heuristic to treat input as full path.
2. Windows absolute paths with backslashes can be misclassified.

Evidence:
1. `src/poly_chat/chat_manager.py:118`

Implementation steps:
1. Replace path classification logic with robust path checks:
   - Use `Path(new_name).is_absolute()`.
   - Consider Windows absolute path detection explicitly (for cross-platform correctness).
2. Keep traversal protections for relative paths.
3. Preserve allowed behavior for simple filenames and in-chats-dir relative names.

Files to edit:
1. `src/poly_chat/chat_manager.py`

Tests to add/update:
1. Add tests for Windows-style absolute path inputs.
2. Preserve existing traversal-prevention tests.

Acceptance criteria:
1. Absolute path handling is platform-correct.
2. Traversal protections remain intact.

---

### P1-04: Mode/provider capability drift after provider switch

Problem:
1. Search/thinking modes are validated only when toggled ON.
2. Switching provider/model can leave unsupported flags enabled.

Evidence:
1. Search on-check only: `src/poly_chat/commands/runtime.py:375`
2. Thinking on-check only: `src/poly_chat/commands/runtime.py:422`
3. Provider can change in `/model`: `src/poly_chat/commands/runtime.py:37`

Implementation steps:
1. Add reconciliation hook whenever provider changes (`/model`, shortcuts, potentially `/model default`).
2. If current provider does not support enabled mode(s), auto-disable and return explicit notice.
3. Keep behavior explicit and predictable in status output.

Files to edit:
1. `src/poly_chat/commands/runtime.py`
2. `src/poly_chat/commands/base.py` (if shared provider-switch hook needed)

Tests to add/update:
1. Enable search/thinking on supported provider, switch to unsupported provider, verify auto-disable.
2. Verify user-facing message includes reason.

Acceptance criteria:
1. Session flags always reflect capabilities of active provider.

---

### P1-05: Citation page overwrite risk

Problem:
1. Citation pages saved with second-level timestamp and citation index.
2. Consecutive responses in same second can collide and overwrite files.

Evidence:
1. Batch timestamp generation: `src/poly_chat/citations.py:155`
2. Filename pattern: `src/poly_chat/page_fetcher.py:81`

Implementation steps:
1. Make filename unique per saved page:
   - Add microseconds and/or short random suffix.
   - Keep citation number for readability.
2. Add last-resort collision loop if target exists.

Files to edit:
1. `src/poly_chat/page_fetcher.py`
2. Optional: `src/poly_chat/citations.py` (if passing stronger timestamp token)

Tests to add/update:
1. Simulate same timestamp writes and ensure unique outputs.

Acceptance criteria:
1. No overwrite under rapid consecutive citation downloads.

---

### P2-01: Blocking `input()` inside async command methods

Problem:
1. Commands call `input()` directly within async handlers.
2. Domain logic and console interaction are tangled.
3. Event loop can be blocked and architecture becomes harder to test.

Evidence:
1. `src/poly_chat/commands/runtime.py:498`
2. `src/poly_chat/commands/runtime.py:548`
3. `src/poly_chat/commands/chat_files.py:121`
4. `src/poly_chat/commands/chat_files.py:212`

Implementation strategy (balanced separation, no over-engineering):
1. Introduce lightweight prompt abstraction (e.g., `UserInteractionPort`).
2. Command layer returns intent/requirements; REPL performs actual prompt I/O.
3. Keep existing signal pattern if desired, but remove direct blocking I/O from command mixins.

Files to edit:
1. `src/poly_chat/commands/runtime.py`
2. `src/poly_chat/commands/chat_files.py`
3. `src/poly_chat/repl.py`
4. Optional new adapter module in `src/poly_chat/ui/`

Tests to add/update:
1. Command tests should no longer monkeypatch `builtins.input` for core flow.
2. REPL-level tests cover confirmation prompts.

Acceptance criteria:
1. Command methods are domain-focused and non-blocking.
2. Interaction logic is isolated and easier to test.

---

### P2-02: Provider protocol signature drift

Problem:
1. Runtime passes `metadata` to `send_message`, but protocol omits it.
2. `get_full_response` signatures differ across provider classes.
3. This increases refactor risk and weakens static verification.

Evidence:
1. Protocol `send_message` lacks metadata: `src/poly_chat/ai/base.py:15`
2. Runtime always passes metadata: `src/poly_chat/ai_runtime.py:107`
3. Provider signature mismatch examples:
   - `src/poly_chat/ai/mistral_provider.py:196`
   - `src/poly_chat/ai/deepseek_provider.py:225`

Implementation steps:
1. Align protocol and all providers to a single contract:
   - `send_message(..., metadata: dict | None = None)`
   - `get_full_response(..., search: bool = False, thinking: bool = False)`
2. Accept unused args where provider does not support feature; ignore safely.
3. Add lightweight interface conformance tests or static type check target.

Files to edit:
1. `src/poly_chat/ai/base.py`
2. All provider modules under `src/poly_chat/ai/`
3. Optional type-check config and docs.

Acceptance criteria:
1. Runtime/provider interface mismatch eliminated.
2. Future provider additions follow one contract.

---

### P2-03: Test import namespace inconsistency (`poly_chat` vs `src.poly_chat`)

Problem:
1. Tests import both namespaces, potentially loading duplicate modules and causing patch-target mismatch.

Evidence:
1. `tests/test_commands_defaults.py:5`
2. `tests/conftest.py:89`

Implementation steps:
1. Standardize tests to `poly_chat.*` imports only.
2. Ensure pytest path config resolves package from `src` consistently.
3. Update patch targets accordingly.

Files to edit:
1. `tests/` files using `src.poly_chat`
2. `pyproject.toml` pytest config only if required for import resolution

Acceptance criteria:
1. Single import namespace in test suite.
2. Mock/patch behavior is consistent and deterministic.

## 5. Execution Order (strict)

Phase 0 (build green baseline):
1. Fix syntax error in `tests/test_orchestrator.py`.
2. Fix profile test fixture drift (`pages_dir`).
3. Run parse + focused test subset.

Phase 1 (P0 runtime correctness):
1. Fix unknown model/helper crash.
2. Fix provider-validation rollback bug.
3. Add targeted tests for both.

Phase 2 (P1 robustness):
1. Chat schema load validation/normalization.
2. Rename path handling fix.
3. Provider capability/mode reconciliation.
4. Citation filename uniqueness.
5. Add tests for each.

Phase 3 (P2 maintainability):
1. Decouple blocking command I/O.
2. Unify provider interface signatures.
3. Normalize test import namespace.

## 6. File-Level Worklist

Core runtime:
1. `src/poly_chat/commands/runtime.py`
2. `src/poly_chat/repl.py`
3. `src/poly_chat/orchestrator.py`
4. `src/poly_chat/chat.py`
5. `src/poly_chat/chat_manager.py`
6. `src/poly_chat/citations.py`
7. `src/poly_chat/page_fetcher.py`
8. `src/poly_chat/ai/base.py`
9. `src/poly_chat/ai/*.py`

Tests:
1. `tests/test_orchestrator.py`
2. `tests/test_profile.py`
3. `tests/test_commands_runtime.py`
4. `tests/test_repl_orchestration.py`
5. `tests/test_chat.py`
6. `tests/test_path_security.py`
7. `tests/test_mode_combinations.py`
8. `tests/test_citations.py`
9. Remaining tests currently importing `src.poly_chat.*`

## 7. Verification Plan

Minimum verification per phase:

Phase 0:
1. `python3 -m compileall -q src tests`

Phase 1 and 2 (targeted):
1. `pytest -q tests/test_commands_runtime.py`
2. `pytest -q tests/test_orchestrator.py`
3. `pytest -q tests/test_repl_orchestration.py`
4. `pytest -q tests/test_chat.py`
5. `pytest -q tests/test_profile.py`
6. `pytest -q tests/test_path_security.py`
7. `pytest -q tests/test_mode_combinations.py`
8. `pytest -q tests/test_citations.py`

Full non-integration suite before release:
1. `pytest -q -m 'not integration'`

Static checks (if configured in environment):
1. `ruff check src tests`
2. `mypy src/poly_chat`

## 8. Definition of Done (overall)

1. Parse and non-integration test suite pass.
2. P0 and P1 issues resolved with explicit tests.
3. P2 changes merged only if they do not delay safe release; otherwise ship P0/P1 and immediately continue on follow-up branch.
4. No behavior regressions in core chat lifecycle (`/new`, `/open`, send, retry, secret, rewind, purge).

## 9. Suggested Commit Slices

1. `fix(tests): unblock collection and align profile fixtures`
2. `fix(commands): remove stale self.session references in model/helper paths`
3. `fix(repl/orchestrator): rollback pending user message on provider validation failure`
4. `fix(chat): validate and normalize loaded chat schema`
5. `fix(chat-manager): robust cross-platform path classification in rename`
6. `fix(runtime): reconcile mode flags after provider/model switch`
7. `fix(citations): prevent saved-page filename collisions`
8. `refactor(commands,repl): remove blocking input from async command methods`
9. `refactor(ai): unify provider protocol and signatures`
10. `test: normalize import namespace and patch targets`

## 10. Risk and Rollback Notes

1. Highest regression risk is phase 3 (interaction boundary refactor). Keep it separate from P0/P1 release if timeline tight.
2. For each phase, ship behind small commits and rerun targeted tests immediately.
3. If a phase introduces instability, revert that commit slice only; do not roll back already-stable P0/P1 fixes.

## 11. Release Cutline Guidance

If release pressure is high, first ship:
1. All P0 issues
2. All P1 issues

Then continue immediately with P2 in next patch release.

This preserves the owner priorities: safe shipping speed first, quality improvements second.
