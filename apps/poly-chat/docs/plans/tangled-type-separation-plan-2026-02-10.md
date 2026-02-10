# PolyChat Tangled Type Separation Plan (2026-02-10)

Status: Proposed
Audience: Maintainers implementing architecture cleanup with low behavioral risk
Primary goal: Untangle high-risk type boundaries that currently rely on implicit string/dict contracts
Non-goal: Performance tuning or broad style-only refactors

## 1. Constraints

1. No micro-optimization work.
2. Keep runtime behavior stable for users.
3. Prioritize type boundary clarity where state/control flow is currently implicit.
4. Ship in small slices with immediate tests after each slice.
5. Preserve time-to-market by using transitional adapters instead of big-bang rewrites.

## 2. Tangled Type Boundaries (Only High-ROI Targets)

### T1: Command result transport is stringly-typed

Problem:
1. `CommandHandler.execute_command` returns `Optional[str]` (`src/poly_chat/commands/__init__.py:23`).
2. Control flow uses magic prefixes like `__NEW_CHAT__:` and `__APPLY_RETRY__:` parsed later by orchestrator (`src/poly_chat/orchestrator.py:75`).
3. This mixes user-facing text and control signals in one raw type.

Impact:
1. Easy to break with typos.
2. Harder to statically verify command/orchestrator contract.
3. Test intent is less explicit.

### T2: Orchestrator action is a single optional-field container

Problem:
1. `OrchestratorAction` has many nullable fields used conditionally by `action` string (`src/poly_chat/orchestrator.py:18`).
2. REPL branches on `action.action` and assumes field combinations (`src/poly_chat/repl.py:155`).
3. Invalid field combinations are representable.

Impact:
1. Hard to reason about legal states.
2. Easy regression risk when adding new action kinds.
3. Weak type guidance for future refactors.

### T3: AI metadata is an untyped cross-layer dict

Problem:
1. `ai_runtime.send_message_to_ai` creates free-form metadata dict (`src/poly_chat/ai_runtime.py:104`).
2. Providers mutate ad-hoc keys (`usage`, `citations`, `thought_callback`, `search_evidence`, etc.).
3. REPL consumes these keys directly (`src/poly_chat/repl.py:219`, `src/poly_chat/repl.py:257`).

Impact:
1. Contract drift risk between providers and runtime.
2. Hidden key mismatches.
3. Difficult to enforce consistency for new providers.

### T4: Session manager blends state model and service logic

Problem:
1. `SessionManager` owns state access, persistence, prompt loading, retry lifecycle, mode lifecycle, and provider cache (`src/poly_chat/session_manager.py:16`, `src/poly_chat/session_manager.py:423`, `src/poly_chat/session_manager.py:508`).
2. The type model is broad and responsibilities are mixed.

Impact:
1. Changes to one concern can unintentionally affect others.
2. Hard to isolate logic in tests.
3. Slower onboarding for contributors.

Note:
1. T4 is higher risk and should be treated as a second-wave separation after T1-T3.

## 3. Proposed Target Types

### 3.1 Commands Contract Types

Add module:
1. `src/poly_chat/commands/types.py`

Define:
1. `CommandTextResult` (for user-visible command output)
2. `CommandSignal` (for control flow with explicit signal enum + payload)
3. `CommandResult` union

Suggested shape:
1. `CommandSignalKind = Literal["exit", "new_chat", "open_chat", "close_chat", "rename_current", "delete_current", "apply_retry", "cancel_retry", "clear_secret_context"]`
2. `CommandSignal(kind: CommandSignalKind, path: str | None = None, value: str | None = None)`
3. `CommandResult = CommandTextResult | CommandSignal | None`

### 3.2 Orchestrator Action Types

Add module:
1. `src/poly_chat/orchestrator_types.py`

Define discriminated actions:
1. `BreakAction`
2. `PrintAction`
3. `ContinueAction`
4. `SendAction` (includes mode/search override/message payload)
5. `OrchestratorAction = BreakAction | PrintAction | ContinueAction | SendAction`

### 3.3 AI Metadata Types

Add module:
1. `src/poly_chat/ai/types.py`

Define:
1. `TokenUsage` TypedDict
2. `Citation` TypedDict
3. `SearchResult` TypedDict (minimal fields currently used)
4. `AIResponseMetadata` TypedDict (total=False) containing currently supported keys

Minimum keys:
1. `model: str`
2. `started: float`
3. `usage: TokenUsage`
4. `citations: list[Citation]`
5. `search_results: list[SearchResult]`
6. `search_executed: bool`
7. `search_evidence: list[str]`
8. `thought_callback: Callable[[str], None]`

### 3.4 Session State Split (Second Wave)

Potential modules:
1. `src/poly_chat/session_types.py` (type-level state containers only)
2. `src/poly_chat/session_persistence.py` (save/load helpers)
3. `src/poly_chat/session_modes.py` (retry/secret/search/thinking transitions)

## 4. Implementation Plan (Phase Order)

## Phase 0: Baseline and Safety Rails

Steps:
1. Freeze baseline: run non-integration suite.
2. Add a short architecture note in the new type modules describing migration intent.
3. Introduce adapters that allow old and new result types during transition.

Acceptance:
1. No behavior change.
2. Existing tests still pass.

## Phase 1: Separate command signal types (T1)

Steps:
1. Create `src/poly_chat/commands/types.py`.
2. Update signal-producing command methods to return `CommandSignal` instead of encoded strings.
3. Keep compatibility adapter in orchestrator:
1. `handle_command_response` accepts both legacy string and new `CommandResult` during migration.
4. Update `CommandHandler.execute_command` return annotation to `CommandResult`.
5. Remove string-prefix parsing once all command paths are migrated.

Files:
1. `src/poly_chat/commands/types.py` (new)
2. `src/poly_chat/commands/__init__.py`
3. `src/poly_chat/commands/chat_files.py`
4. `src/poly_chat/commands/runtime.py`
5. `src/poly_chat/orchestrator.py`
6. `tests/test_orchestrator.py`
7. `tests/test_repl_orchestration.py`

Acceptance:
1. No remaining `__SIGNAL__` string parsing in command->orchestrator contract.
2. All command control paths use typed signal objects.

## Phase 2: Split orchestrator actions into discriminated types (T2)

Steps:
1. Create `src/poly_chat/orchestrator_types.py`.
2. Replace monolithic `OrchestratorAction` dataclass with union types.
3. Update orchestrator methods to return exact action class.
4. Update REPL dispatch to pattern-match by class/type, not action string + optional fields.
5. Add assertions/tests for invalid action construction impossible by type.

Files:
1. `src/poly_chat/orchestrator_types.py` (new)
2. `src/poly_chat/orchestrator.py`
3. `src/poly_chat/repl.py`
4. `tests/test_orchestrator.py`

Acceptance:
1. REPL no longer checks nullable field combinations for action validity.
2. Action types encode legal payloads explicitly.

## Phase 3: Type AI metadata contract (T3)

Steps:
1. Create `src/poly_chat/ai/types.py`.
2. Change `send_message_to_ai` metadata type from `dict` to `AIResponseMetadata`.
3. Update provider method signatures to accept `AIResponseMetadata | None`.
4. Standardize metadata helper writes to shared helper functions where possible.
5. Update REPL consumers to use typed lookups and defaults.

Files:
1. `src/poly_chat/ai/types.py` (new)
2. `src/poly_chat/ai_runtime.py`
3. `src/poly_chat/ai/base.py`
4. `src/poly_chat/ai/*.py`
5. `src/poly_chat/repl.py`
6. Provider-focused tests (existing + targeted additions)

Acceptance:
1. Metadata keys used in runtime are represented in one typed schema.
2. Provider additions have one clear metadata contract.

## Phase 4: Session manager concern split (T4, optional second wave)

Steps:
1. Extract persistence helpers first (lowest risk).
2. Extract mode transition helpers next.
3. Keep `SessionManager` as facade until all call sites migrate.
4. Move only one concern per commit.

Files:
1. `src/poly_chat/session_manager.py`
2. `src/poly_chat/session_types.py` (new)
3. `src/poly_chat/session_persistence.py` (new)
4. `src/poly_chat/session_modes.py` (new)
5. Session-related tests

Acceptance:
1. `SessionManager` becomes facade/orchestrator, not implementation bucket.
2. Retry/secret/persistence logic are independently testable modules.

## 5. Testing Strategy Per Phase

Common gate after each phase:
1. `python3 -m compileall -q src tests`
2. `.venv/bin/pytest -q -m 'not integration'`

Type-focused gate:
1. `.venv/bin/mypy src/poly_chat`

Phase-specific targeted tests:
1. Commands/orchestrator: `tests/test_orchestrator.py`, `tests/test_repl_orchestration.py`, `tests/test_commands_*.py`
2. AI metadata: provider tests + `tests/test_streaming.py` and chat flow tests
3. Session split: `tests/test_session_manager.py`, `tests/test_session_state.py`

## 6. Risk Controls

1. Use compatibility adapters before deleting legacy paths.
2. Keep commits small and reversible.
3. For Phase 1 and 2, add temporary dual-path support for one commit window.
4. Do not combine T4 with T1-T3 release-critical changes.

## 7. Suggested Commit Slices

1. `refactor(commands): introduce typed command result and signal objects`
2. `refactor(orchestrator): migrate command signal handling to typed contract`
3. `refactor(orchestrator,repl): replace monolithic action dataclass with discriminated action types`
4. `refactor(ai): add typed AI response metadata contract and migrate providers`
5. `refactor(session): extract persistence helpers from SessionManager` (optional wave 2)
6. `refactor(session): extract mode lifecycle helpers` (optional wave 2)

## 8. Tomorrow Execution Checklist

1. Implement Phase 1 fully and run full non-integration tests.
2. If Phase 1 passes cleanly, implement Phase 2.
3. Only start Phase 3 if time remains and tests are still green.
4. Defer Phase 4 unless there is explicit bandwidth.

## 9. Definition of Done

1. T1-T3 completed with all tests green.
2. No remaining magic signal strings in command/orchestrator boundary.
3. No remaining optional-field action container in orchestrator/REPL boundary.
4. AI metadata contract documented in code and used consistently.
5. Optional T4 deferred or completed in separate follow-up branch.
