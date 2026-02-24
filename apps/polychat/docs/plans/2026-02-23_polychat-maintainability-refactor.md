# PolyChat Maintainability Refactor Plan

Implementation plan generated on 2026-02-23.

## Objective

Improve long-term maintainability of PolyChat by reducing hidden coupling, introducing strong typing at module boundaries, and decomposing oversized modules into focused units.

## Progress Update (2026-02-24)

1. Baseline quality gates are now green:
   - `pytest -q`: `544 passed, 3 deselected`
   - `mypy src/polychat`: `Success: no issues found in 98 source files`
   - `ruff check src tests`: pass
2. Phase 1 now has typed domain boundaries for chat and profile:
   - Added `src/polychat/domain/chat.py` and `src/polychat/domain/__init__.py`.
   - Added `src/polychat/domain/profile.py`.
   - `src/polychat/chat/storage.py` now normalizes via `ChatDocument`.
   - `src/polychat/chat/messages.py` now constructs messages via `ChatMessage`.
   - `src/polychat/profile.py` now crosses a typed boundary via `RuntimeProfile`.
3. Added domain tests at `tests/test_domain_chat.py` and `tests/test_domain_profile.py`.
4. Phase 2 started with explicit command dependency wiring:
   - Added `src/polychat/commands/context.py` (`CommandContext`).
   - `CommandHandlerBaseMixin` now composes dependencies through `self.context`.
   - Added `tests/test_commands_context.py`.
5. Phase 2 command migration (batch 1 and 2) is complete:
   - `src/polychat/commands/misc.py` now uses explicit `MiscCommandHandlers` with adapter methods.
   - `src/polychat/commands/chat_files.py` now uses explicit `ChatFileCommandHandlers` with adapter methods.
   - `CommandHandler` now owns explicit handler instances and keeps existing command method surface.
6. Phase 2 command migration (batch 3) is complete:
   - `src/polychat/commands/runtime_models.py` now uses explicit `RuntimeModelCommandHandlers` with adapter methods.
   - `src/polychat/commands/runtime_modes.py` now uses explicit `RuntimeModeCommandHandlers` with adapter methods.
   - Added runtime-handler wiring assertions in `tests/test_commands_context.py`.
7. Phase 2 command migration (batch 4) is complete:
   - `src/polychat/commands/meta_generation.py` now uses explicit `MetadataGenerationCommandHandlers`.
   - `src/polychat/commands/meta_inspection.py` now uses explicit `MetadataInspectionCommandHandlers`.
   - `src/polychat/commands/runtime_mutation.py` also now uses explicit `RuntimeMutationCommandHandlers` for consistency.
8. Phase 3 started with SessionManager facade thinning:
   - Added `src/polychat/session/accessors.py` for typed state descriptors and dict/snapshot helpers.
   - `src/polychat/session_manager.py` now delegates state access via `StateField` and access helpers.
   - `session_manager.py` reduced from 633 to 499 lines while preserving public API behavior.
9. Phase 3 orchestration transition extraction started:
   - Added `src/polychat/orchestration/retry_transitions.py` to centralize `/apply` retry replacement rules.
   - `src/polychat/orchestration/signals.py` now delegates retry replacement to explicit helper logic.
   - Added focused tests in `tests/test_orchestration_retry_transitions.py`.
10. Phase 3 signal routing hardening continued:
   - `src/polychat/orchestration/signals.py` now uses an explicit command-signal dispatch table.
   - Added payload validation tests for missing/invalid command signal fields in `tests/test_orchestrator.py`.

## Baseline Findings (At Plan Creation)

1. Large modules with mixed responsibilities:
   - `src/polychat/session_manager.py` (736 lines)
   - `src/polychat/orchestrator.py` (663 lines)
   - `src/polychat/commands/runtime.py` (634 lines)
   - `src/polychat/logging_utils.py` (528 lines)
2. Typing debt is high:
   - `mypy src/polychat` reports 292 errors across 25 files.
   - Errors include `dict[str, Any]` overuse, optionality leaks, and mixin attribute ambiguity.
3. Command architecture is hard to reason about:
   - Cross-mixin hidden dependencies in `src/polychat/commands/*.py`.
   - Runtime control flow encoded as mixed string responses and control signals.
4. Provider implementations repeat similar request/stream/error patterns:
   - `src/polychat/ai/*_provider.py` repeats shared patterns with provider-specific branches.

## Refactor Recommendations

### R1. Introduce typed domain models at core boundaries

Files:
- `src/polychat/chat.py`
- `src/polychat/session_manager.py`
- `src/polychat/orchestrator.py`
- `src/polychat/repl.py`
- `src/polychat/profile.py`
- `src/polychat/ai/types.py`

Current state:
- Core data flows use raw dictionaries (`dict[str, Any]`) for chat messages, metadata, retry attempts, and profile data.
- Optional fields are handled ad hoc, causing nullability and shape assumptions to leak.

Proposed state:
- Add a `src/polychat/domain/` package with typed models (dataclass or Pydantic) for:
  - `ChatMessage`, `ChatMetadata`, `ChatDocument`
  - `RetryAttempt`, `RetryState`, `SecretState`
  - `ProfileConfig` (or `RuntimeProfileView`)
- Keep serialization/deserialization at IO boundaries (`chat.py`, `profile.py`), with internal logic using typed models.

Rationale:
- Typed boundaries reduce accidental schema drift and make refactors safer.
- This directly lowers mypy noise and improves correctness readability.

### R2. Replace mixin-heavy command internals with explicit command context

Files:
- `src/polychat/commands/base.py`
- `src/polychat/commands/runtime.py`
- `src/polychat/commands/chat_files.py`
- `src/polychat/commands/metadata.py`
- `src/polychat/commands/misc.py`
- `src/polychat/commands/__init__.py`

Current state:
- Command mixins implicitly depend on attributes and helper methods defined elsewhere.
- Static analysis reports many `attr-defined` issues due to hidden composition.

Proposed state:
- Introduce `CommandContext` and `Command` protocol/object model:
  - `context` contains session access, interaction port, and shared helpers.
  - each command becomes an explicit handler object/function with declared dependencies.
- Keep current command strings and UX unchanged; refactor internals only.

Rationale:
- Removes hidden coupling and makes command behavior locally understandable.
- Improves testability and type-checkability without behavior change.

### R3. Split `SessionManager` by concern and keep a thin facade

Files:
- `src/polychat/session_manager.py`
- new modules under `src/polychat/session/`:
  - `state_access.py`
  - `chat_lifecycle.py`
  - `retry_state.py`
  - `secret_state.py`
  - `provider_cache.py`

Current state:
- `SessionManager` owns many unrelated concerns: state, chat switching, retry/secret logic, path/system prompt loading, timeout, provider cache, ID mapping.

Proposed state:
- Extract concern-specific services; keep `SessionManager` as compatibility facade and composition root.
- Move heavy methods into dedicated modules with focused unit tests.

Rationale:
- Smaller modules reduce cognitive load and change blast radius.
- Enables incremental hardening of each subsystem.

### R4. Decompose orchestrator into mode handlers and transition rules

Files:
- `src/polychat/orchestrator.py`
- `src/polychat/orchestrator_types.py`
- new modules under `src/polychat/orchestration/`:
  - `command_signal_router.py`
  - `message_flow.py`
  - `retry_mode.py`
  - `secret_mode.py`
  - `error_mode.py`

Current state:
- Orchestrator interleaves command-signal handling, mode transitions, message lifecycle, and persistence logic in one large class.

Proposed state:
- Create per-mode handlers with explicit transition contracts.
- Keep existing action types (`BreakAction`, `ContinueAction`, `PrintAction`, `SendAction`) but narrow input/output types.

Rationale:
- Makes transition rules explicit and easier to test.
- Prevents regressions in retry/secret/error behavior.

### R5. Consolidate provider shared logic into reusable utilities

Files:
- `src/polychat/ai/openai_provider.py`
- `src/polychat/ai/claude_provider.py`
- `src/polychat/ai/gemini_provider.py`
- `src/polychat/ai/grok_provider.py`
- `src/polychat/ai/perplexity_provider.py`
- `src/polychat/ai/mistral_provider.py`
- `src/polychat/ai/deepseek_provider.py`
- `src/polychat/ai_runtime.py`
- new modules:
  - `src/polychat/ai/http_error_mapping.py`
  - `src/polychat/ai/streaming_common.py`
  - `src/polychat/ai/citation_normalization.py`

Current state:
- Each provider repeats similar patterns for:
  - streaming loops
  - usage extraction
  - timeout/retry error reporting
  - citation post-processing

Proposed state:
- Extract provider-agnostic utility helpers and normalized response adapters.
- Keep provider-specific request payload shaping in provider modules.

Rationale:
- Reduces duplication and drift across providers.
- Speeds future provider updates and bug fixes.

### R6. Split logging schema from formatting and event emission

Files:
- `src/polychat/logging_utils.py`
- `src/polychat/cli.py`
- `src/polychat/repl.py`
- new modules:
  - `src/polychat/logging/events.py`
  - `src/polychat/logging/formatter.py`
  - `src/polychat/logging/sanitization.py`

Current state:
- One module mixes sanitization, event schema ordering, formatting, event emission, retry hooks, and path resolution.

Proposed state:
- Separate:
  - structured event field definitions
  - formatter implementation
  - sanitization/resolution helpers
- Keep `log_event()` public API stable during migration.

Rationale:
- Clarifies ownership and makes logging behavior easier to extend safely.

### R7. Centralize path and prompt resolution policy

Files:
- `src/polychat/path_utils.py`
- `src/polychat/profile.py`
- `src/polychat/session_manager.py`
- `src/polychat/commands/runtime.py`
- `src/polychat/commands/base.py`

Current state:
- Path validation and prompt-path loading checks are split across multiple modules.
- Some validations happen late and duplicate logic.

Proposed state:
- Introduce one policy layer for path classes:
  - mapped shortcuts (`~`, `@`)
  - platform-absolute paths
  - chat-directory constrained relative paths
- Reuse it from profile loading, command handlers, and session prompt loading.

Rationale:
- Improves consistency and reduces security edge-case duplication.

### R8. Make docs/help text single-source and generated

Files:
- `src/polychat/commands/misc.py`
- `README.md`
- tests:
  - `tests/test_docs_conformance.py`
  - `tests/test_docs_readme.py`

Current state:
- Command behavior/help/readme sections are maintained in multiple places.
- Drift risk increases as command set grows.

Proposed state:
- Introduce command metadata registry (name, args, description, aliases, examples).
- Generate `/help` text and README command sections from the registry.

Rationale:
- Prevents documentation drift and lowers maintenance overhead.

### R9. Establish progressive quality gates with explicit targets

Files:
- `pyproject.toml`
- `tests/`
- optional scripts in `scripts/`

Current state:
- Tests are strong, but typing is not gate-ready.
- Linting currently catches low-level issues, but type safety is noisy.

Proposed state:
- Introduce staged gates:
  1. `mypy` strict on new/low-coupling modules first (`domain/`, `session/`, `orchestration/`).
  2. Incrementally include legacy modules as they are refactored.
  3. CI gate: fail on new typing errors in targeted packages.

Rationale:
- Enables forward progress without blocking all work on existing debt.

## Detailed Execution Tasklist

### Phase 0: Safety rails and baselines

- [x] Capture frozen baseline:
  - `pytest -q`
  - `mypy src/polychat` error report snapshot
  - file-size hotspot snapshot
- [x] Add temporary architecture notes in `docs/` for migration scope and invariants.

### Phase 1: Typed domain layer

- [x] Implement domain models and serializers.
- [x] Migrate `chat` and `profile` boundaries first.
- [x] Update unit tests for model parsing and backward-compatible JSON shape handling.

Dependencies:
- none

### Phase 2: Command subsystem refactor

- [x] Add `CommandContext` and explicit command handler contracts.
- [x] Port commands from mixin methods to explicit command handlers in small batches:
  - [x] misc/help/exit
  - [x] chat file commands
  - [x] runtime model/mode commands
  - [x] metadata/history/safety commands
- [x] Keep legacy adapter layer until all handlers are migrated.

Dependencies:
- Phase 1 typed models (partial)

### Phase 3: Session/orchestrator decomposition

- [x] Extract `session/` submodules and reduce `SessionManager` to facade.
- [ ] Extract orchestration mode handlers and signal routing.
  - [x] Extract retry-apply transition rules to dedicated helper module.
  - [x] Replace command-signal `if` chain with explicit dispatch table and payload validators.
- [ ] Add transition-invariant tests:
  - retry mode entry/exit
  - apply/cancel semantics
  - secret mode persistence boundaries
  - pending-error gating behavior

Dependencies:
- Phase 2 command contracts

### Phase 4: Provider/logging consolidation

- [ ] Extract shared provider utilities and migrate providers one by one.
- [ ] Split logging module into schema/formatter/sanitization components.
- [ ] Preserve log field compatibility for existing parsers.

Dependencies:
- Phase 1 typed metadata models

### Phase 5: Docs/help generation and quality gates

- [ ] Create command metadata registry and generator.
- [ ] Update README generation workflow and tests.
- [ ] Turn on staged mypy enforcement for refactored packages.
- [ ] Define "no new debt" policy:
  - no new `dict[str, Any]` in core flows
  - no new module >500 lines without explicit split rationale

Dependencies:
- Phases 2-4

## Acceptance Criteria

1. Core subsystems are decomposed with clear ownership and smaller modules.
2. Mypy errors are reduced substantially and isolated to known legacy areas.
3. Command internals no longer rely on mixin hidden attributes.
4. Retry/secret/error mode behavior is covered by focused transition tests.
5. Provider and logging common logic is centralized with no behavior regressions.
6. README and `/help` are generated from a single command metadata source.

## Risks and Mitigations

1. Risk: Behavioral regressions in retry/secret flows.
   Mitigation: Add characterization tests before refactor and keep migration incremental.
2. Risk: Large PRs become hard to review.
   Mitigation: Ship by phase with bounded file scopes and compatibility adapters.
3. Risk: Type migrations slow feature work.
   Mitigation: Use progressive mypy targets and avoid repo-wide strictness in one jump.

## Suggested PR Breakdown

1. PR-1: Domain models + boundary adapters (`chat.py`, `profile.py`)
2. PR-2: Command context + first command batch
3. PR-3: Remaining command migration + optional legacy adapter cleanup
4. PR-4: Session decomposition
5. PR-5: Orchestrator decomposition + transition tests
6. PR-6: Provider shared utilities
7. PR-7: Logging split
8. PR-8: Docs/help generator + staged mypy gate
