# PolyChat Concern Consolidation Refactor Plan

Implementation plan generated on 2026-02-24.

## Objective

Improve maintainability by merging over-fragmented same-concern modules while preserving separation of concerns, behavior, and public compatibility.

## Scope

- Source code only under `src/polychat/` and supporting tests under `tests/`.
- Skip docs-only and style-only changes, except where architecture docs must record rationale.

## Baseline Findings (2026-02-24)

1. Many modules were split for earlier refactors but are now micro-modules with a single caller and shared reason-to-change.
   - Session micro-modules (`session/accessors.py`, `session/chat_lifecycle.py`, `session/messages.py`, `session/modes.py`, `session/persistence.py`, `session/provider_cache.py`, `session/settings.py`, `session/system_prompt.py`, `session/timeouts.py`) are all imported by `session_manager.py` and mostly not used elsewhere.
   - REPL micro-modules (`repl/input.py`, `repl/status_banners.py`) are only consumed by `repl/loop.py`.
   - Command composition wrappers (`commands/runtime.py`, `commands/metadata.py`) are thin pass-through files with no standalone behavior.
2. Orchestration transition modules are highly granular for the current code size.
   - `orchestration/retry_transitions.py` and `orchestration/response_transitions.py` are helper-only policy modules with one production caller each.
3. Command dispatch metadata is split across files with tightly coupled lifecycle.
   - `commands/registry.py` and `commands/dispatcher.py` are always edited together when commands are added or renamed.
4. API key backend loaders are split by storage type but have one caller path.
   - `keys/env_vars.py`, `keys/json_files.py`, `keys/keychain.py`, and `keys/credential_manager.py` are consumed only through `keys/loader.py`.
5. Some module placement remains less discoverable than feature-local alternatives.
   - Citation normalization runtime lives at `src/polychat/citations.py` but is used by AI send flow (`repl/send_pipeline.py`) and AI metadata concerns.

## Refactor Recommendations

### R1. Consolidate session operation modules under one cohesive operations unit

Files:
- `src/polychat/session_manager.py`
- `src/polychat/session/accessors.py`
- `src/polychat/session/chat_lifecycle.py`
- `src/polychat/session/messages.py`
- `src/polychat/session/modes.py`
- `src/polychat/session/persistence.py`
- `src/polychat/session/provider_cache.py`
- `src/polychat/session/settings.py`
- `src/polychat/session/system_prompt.py`
- `src/polychat/session/timeouts.py`

Current state:
- Session behavior is spread across many files with single-caller fan-in patterns.
- Common session changes require editing multiple tiny modules and wiring imports in `session_manager.py`.

Proposed state:
- Keep `session/state.py` as the canonical state model.
- Merge the remaining session helper modules into `session/operations.py` (or `session/runtime.py`) with clear internal sections:
  - state descriptors/access
  - lifecycle
  - modes
  - message hex-id helpers
  - persistence
  - provider cache
  - runtime settings/system prompt helpers
- Keep `session_manager.py` as a facade/composition boundary.

Rationale:
- Same concern (session behavior) with one primary caller should optimize for local readability over file count.
- Consolidation keeps boundaries intact while reducing navigation overhead.

### R2. Consolidate orchestration transition policies into flow modules

Files:
- `src/polychat/orchestration/signals.py`
- `src/polychat/orchestration/response_handlers.py`
- `src/polychat/orchestration/retry_transitions.py`
- `src/polychat/orchestration/response_transitions.py`
- `tests/test_orchestration_retry_transitions.py`
- `tests/test_orchestration_response_transitions.py`

Current state:
- Transition policy helpers are split into separate files despite one production caller each.
- Flow comprehension requires jumping between mixin and transition files.

Proposed state:
- Merge retry replacement policy into command-signal flow module.
- Merge response transition policy into response handling flow module.
- Preserve test coverage by either:
  - migrating tests to the merged module symbols, or
  - keeping temporary re-export shims during transition.

Rationale:
- These are implementation details of one orchestration flow, not reusable shared subsystems.
- Fewer files improves reasoning about mode transitions.

### R3. Fold REPL input/banner helpers back into loop module

Files:
- `src/polychat/repl/loop.py`
- `src/polychat/repl/input.py`
- `src/polychat/repl/status_banners.py`

Current state:
- `input.py` and `status_banners.py` are single-caller helpers for loop wiring.

Proposed state:
- Merge prompt session creation, key bindings, and banner rendering into `repl/loop.py` under well-labeled internal sections.
- Keep `repl/send_pipeline.py` separate (distinct provider/send concern).

Rationale:
- Input/banners are direct loop concerns and not meaningfully reusable.
- Consolidation reduces indirection in the most frequently read runtime entrypoint.

### R4. Simplify commands package composition files

Files:
- `src/polychat/commands/__init__.py`
- `src/polychat/commands/runtime.py`
- `src/polychat/commands/metadata.py`
- `src/polychat/commands/registry.py`
- `src/polychat/commands/dispatcher.py`
- `src/polychat/commands/command_docs.py`
- `src/polychat/commands/command_docs_models.py`

Current state:
- `runtime.py` and `metadata.py` are composition-only shims.
- `registry.py` and `dispatcher.py` are tightly coupled but split.
- `command_docs_models.py` contains tiny dataclasses only used by command docs.

Proposed state:
- Compose runtime/metadata mixins directly in `commands/__init__.py` and remove composition-only wrappers.
- Merge command spec registry + dispatcher into a single `commands/dispatch.py`.
- Merge command-doc dataclasses into `command_docs.py` (keep `command_docs_data.py` separate due large static data).

Rationale:
- Reduces file hopping for core command dispatch understanding.
- Removes wrappers that add no domain boundary.

### R5. Merge key backend loaders behind one backend module

Files:
- `src/polychat/keys/loader.py`
- `src/polychat/keys/env_vars.py`
- `src/polychat/keys/json_files.py`
- `src/polychat/keys/keychain.py`
- `src/polychat/keys/credential_manager.py`

Current state:
- Backend-specific modules are only called by `keys/loader.py`.

Proposed state:
- Create `keys/backends.py` containing all backend load/store functions.
- Keep `keys/loader.py` as the public selection/validation API.

Rationale:
- One concern (credential backends) with one integration point should be locally discoverable.
- Consolidates platform behavior and shared error wording in one place.

### R6. Improve module placement for AI citation runtime concerns

Files:
- `src/polychat/citations.py`
- `src/polychat/repl/send_pipeline.py`
- `tests/test_citations.py`

Current state:
- Citation normalization and redirect resolution live at root module level.

Proposed state:
- Move to `src/polychat/ai/citations.py`.
- Keep `src/polychat/citations.py` as a compatibility shim re-export until imports/tests are migrated.

Rationale:
- Citation normalization is AI response post-processing and belongs with AI runtime utilities.
- Improves directory-level discoverability.

### R7. Consolidate timeout normalization policy (remove duplicate session helper policy)

Files:
- `src/polychat/timeouts.py`
- `src/polychat/session/timeouts.py`
- `src/polychat/session_manager.py`

Current state:
- Timeout normalization/formatting policy exists both in root timeout policy and session helper module.

Proposed state:
- Keep one canonical timeout policy module (`src/polychat/timeouts.py`) and remove duplicated session-level timeout helper file.
- `session_manager.py` should consume canonical policy APIs.

Rationale:
- Single source of truth avoids drift in input validation and display formatting.

## Detailed Execution Tasklist

### Phase 0: Safety and invariants

- [x] Freeze baseline quality gates before structural merges:
  - `ruff check src tests`
  - `mypy src/polychat`
  - `pytest -q`
- [x] Document merge rationale in `docs/architecture/module-ownership.md` before deleting any module-level shims.

### Phase 1: Session consolidation

- [x] Introduce `src/polychat/session/operations.py` and move helpers from session micro-modules (except `state.py`).
- [x] Update `session_manager.py` imports/calls to new module.
- [x] Keep temporary re-export shims for moved module paths if tests/importers rely on old targets.
- [x] Run focused tests:
  - `tests/test_session_manager.py`
  - `tests/test_session_state.py`
  - orchestration mode invariant tests.

### Phase 2: Orchestration consolidation

- [x] Merge transition helper modules into flow modules (`signals` and `response_handlers`).
- [x] Update or replace transition-module tests to assert equivalent behavior through merged symbols.
- [x] Keep compatibility imports briefly if needed, then remove once references are migrated.

### Phase 3: REPL consolidation

- [x] Merge `repl/input.py` and `repl/status_banners.py` into `repl/loop.py`.
- [x] Preserve `repl/__init__.py` public entrypoint.
- [x] Run focused tests:
  - `tests/test_streaming.py`
  - `tests/test_repl_orchestration.py`

### Phase 4: Commands consolidation

- [x] Remove composition-only wrappers (`commands/runtime.py`, `commands/metadata.py`) and compose directly in `commands/__init__.py`.
- [x] Merge `commands/registry.py` + `commands/dispatcher.py` into one dispatch module.
- [x] Merge `commands/command_docs_models.py` into `commands/command_docs_data.py`.
- [x] Update tests that import concrete handler classes from old module paths.

### Phase 5: Keys and placement cleanup

- [x] Create `keys/backends.py` and migrate backend loader/store logic.
- [x] Move citation runtime logic to `ai/citations.py`, migrate imports, and retire the root shim.
- [x] Consolidate timeout policy onto root `timeouts.py` and remove session duplicate.

### Phase 6: Shim retirement and policy alignment

- [x] Remove temporary compatibility shims once no in-repo imports depend on them.
- [x] Update `docs/architecture/module-ownership.md` with merged module ownership.
- [x] Revisit maintainability policy thresholds/tests if they enforce fragmentation over cohesion.

### Phase 7: Final validation

- [x] Run full gates:
  - `ruff check src tests`
  - `mypy src/polychat`
  - `pytest -q`
- [x] Record final module map and changed ownership boundaries.

## Completion Update (2026-02-24)

Validation results:
- `ruff check src tests`: pass
- `mypy src/polychat`: `Success: no issues found in 89 source files`
- `pytest -q`: `575 passed, 3 deselected, 1 warning`

Final module map updates:
- Session runtime helpers consolidated into `src/polychat/session/operations.py`.
- Orchestration transition helpers consolidated into:
  - `src/polychat/orchestration/signals.py`
  - `src/polychat/orchestration/response_handlers.py`
- REPL input/banner helpers consolidated into `src/polychat/repl/loop.py`.
- Commands dispatch consolidated into `src/polychat/commands/dispatch.py`.
- Command docs models consolidated into `src/polychat/commands/command_docs_data.py`.
- Key backend loaders consolidated into `src/polychat/keys/backends.py`.
- Citation runtime moved to `src/polychat/ai/citations.py`; root shim removed.
- Session timeout duplication removed; canonical timeout validation/formatting now lives in `src/polychat/timeouts.py`.

Removed modules:
- `src/polychat/session/chat_lifecycle.py`
- `src/polychat/session/messages.py`
- `src/polychat/session/modes.py`
- `src/polychat/session/persistence.py`
- `src/polychat/session/provider_cache.py`
- `src/polychat/session/settings.py`
- `src/polychat/session/system_prompt.py`
- `src/polychat/session/timeouts.py`
- `src/polychat/orchestration/retry_transitions.py`
- `src/polychat/orchestration/response_transitions.py`
- `src/polychat/repl/input.py`
- `src/polychat/repl/status_banners.py`
- `src/polychat/commands/runtime.py`
- `src/polychat/commands/metadata.py`
- `src/polychat/commands/dispatcher.py`
- `src/polychat/commands/command_docs_models.py`
- `src/polychat/keys/env_vars.py`
- `src/polychat/keys/json_files.py`
- `src/polychat/keys/keychain.py`
- `src/polychat/keys/credential_manager.py`
- `src/polychat/citations.py`

## Rollback Strategy

- Keep merges incremental and reversible by phase.
- Use compatibility re-export shims during migration; remove only after import graph is clean.
- If regressions appear, revert only the current phase and keep prior phases intact.

## Success Criteria

1. Session/orchestration/repl/commands key paths require fewer cross-file jumps for routine edits.
2. No behavior regressions in command flow, retry/apply semantics, secret mode, and chat persistence.
3. Quality gates remain green (`ruff`, `mypy`, `pytest`).
4. Package boundaries remain concern-driven (not size-driven) and documented.
