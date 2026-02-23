# tk Maintainability Refactor Plan

Refactor plan generated on 2026-02-23.

## Objective

Improve long-term maintainability of `tk` while preserving user-visible behavior and command UX.

## Scope

- In scope: structure, typing, module boundaries, parser robustness, test quality, and quality gates.
- Out of scope: feature expansion, output format redesign, persistence format migration beyond compatibility adapters.

## Recommendation 1: Introduce typed domain models and DTOs

### File references

- `src/tk/data.py`
- `src/tk/commands.py`
- `src/tk/formatters.py`
- `src/tk/session.py`
- `src/tk/profile.py`
- `tests/conftest.py`

### Current state

- Core entities (task, profile, list/history payloads) are passed as `dict[str, Any]`.
- Field contracts are implicit and spread across modules (`"status"`, `"subjective_date"`, `"items"`, `"groups"`).
- Validation is mostly runtime and string-key based.

### Proposed state

- Add `src/tk/models.py` with explicit models:
  - `TaskStatus` enum.
  - `Task` dataclass.
  - `Profile` dataclass.
  - `PendingListItem`, `HistoryGroup`, and payload dataclasses.
- Keep JSON storage schema stable by adding serializer/deserializer helpers in a single adapter module.
- Update public function signatures to consume/return typed models where possible.

### Rationale

- Reduces hidden contracts and accidental key typos.
- Improves editor support and readability.
- Makes cross-module changes safer and easier to review.

### Detailed tasks

1. Add models and conversion helpers with backward-compatible JSON mapping.
2. Migrate `commands` return payloads to typed DTOs.
3. Update `formatters` to consume DTOs directly.
4. Update `Session` to hold typed profile/tasks.
5. Update tests to use model factories instead of ad-hoc dict literals where practical.

## Recommendation 2: Split `data.py` by responsibility

### File references

- `src/tk/data.py`
- `src/tk/markdown.py`
- `src/tk/commands.py`
- `tests/test_data.py`

### Current state

- `data.py` contains persistence (load/save), schema validation, CRUD operations, and display-oriented grouping.
- Query/presentation helpers and storage concerns are coupled.

### Proposed state

- Split into focused modules:
  - `src/tk/repository.py` for file I/O (`load_tasks`, `save_tasks`).
  - `src/tk/task_schema.py` for JSON/schema validation.
  - `src/tk/task_ops.py` for CRUD operations.
  - `src/tk/task_queries.py` for grouping/sorting/query helpers.
- Keep `src/tk/data.py` as a compatibility facade during migration, then remove it after all call sites are updated.

### Rationale

- Clear boundaries reduce fear of change.
- Unit tests become more targeted.
- Future persistence changes stay isolated.

### Detailed tasks

1. Extract modules without changing behavior.
2. Move tests to match new module boundaries.
3. Add compatibility imports in `data.py`.
4. Update imports incrementally across codebase.
5. Remove compatibility layer once migration is complete.

## Recommendation 3: Decompose command logic into focused modules

### File references

- `src/tk/commands.py`
- `src/tk/dispatcher.py`
- `tests/test_commands.py`
- `tests/test_dispatcher.py`

### Current state

- `commands.py` combines list/history querying, mutation commands, sync behavior, and date helpers.
- The file mixes multiple concerns and is a central hotspot.

### Proposed state

- Split command logic into:
  - `src/tk/commands_mutation.py` (`add`, `done`, `cancel`, `edit`, `delete`, `note`, `date`).
  - `src/tk/commands_query.py` (`list`, `history`, `today`, `yesterday`, `recent` payload builders).
  - `src/tk/commands_sync.py` (`sync`, auto-sync helpers).
  - `src/tk/commands_shared.py` for shared utilities.
- Keep `dispatcher.py` orchestration-only.

### Rationale

- Lower cognitive load per module.
- Better ownership boundaries for future changes.
- Easier code review and debugging.

### Detailed tasks

1. Identify function groups and move with tests unchanged.
2. Preserve public API surface via re-export module during transition.
3. Update `dispatcher` imports to focused modules.
4. Remove re-export shim when migration is stable.

## Recommendation 4: Introduce explicit exception types and boundary mapping

### File references

- `src/tk/repl.py`
- `src/tk/cli.py`
- `src/tk/dispatcher.py`
- `src/tk/profile.py`
- `src/tk/validation.py`

### Current state

- Most expected user-facing failures use `ValueError` with string-based distinctions.
- REPL and CLI handle broad categories, reducing semantic clarity.

### Proposed state

- Add `src/tk/errors.py` with explicit exceptions:
  - `TkValidationError`
  - `TkUsageError`
  - `TkStorageError`
  - `TkConfigError`
- Raise semantic exceptions from domain modules.
- Map exceptions to user-facing messages at CLI/REPL boundaries.

### Rationale

- Improves readability and intent.
- Reduces coupling to message strings in tests.
- Enables cleaner error reporting behavior as app grows.

### Detailed tasks

1. Define exception hierarchy.
2. Migrate high-traffic failure paths first (`profile`, `dispatcher`, `commands`).
3. Update REPL/CLI catch blocks to target semantic categories.
4. Update tests to assert exception type plus critical message content.

## Recommendation 5: Replace manual command parsing with robust tokenization

### File references

- `src/tk/repl.py`
- `src/tk/dispatcher.py`
- `tests/test_repl.py`

### Current state

- Parser uses `line.split()`, which does not support quoted arguments.
- Flag parsing is partly command-specific and partly generic.

### Proposed state

- Use `shlex.split` for tokenization.
- Keep command policy explicit in dispatcher metadata:
  - Commands that treat `--` text as literal content.
  - Commands that accept flags.
- Introduce parser tests for quotes/escaping edge cases.

### Rationale

- Cleaner parser semantics with fewer edge-case surprises.
- Better maintainability than custom token logic.

### Detailed tasks

1. Replace raw split with `shlex.split` and preserve existing behavior contracts.
2. Add compatibility tests for current behavior and new quoting behavior.
3. Update help text where behavior becomes clearer for users.

## Recommendation 6: Create a single source of truth for command metadata/help

### File references

- `src/tk/dispatcher.py`
- `src/tk/repl.py`
- `README.md`
- `tests/test_dispatcher.py`

### Current state

- Command usage/help is manually duplicated in static help text and README.
- Drift risk increases with each command/usage change.

### Proposed state

- Expand `CommandHandler` metadata to include description, usage, aliases, and flag support.
- Generate REPL help output from registry metadata.
- Add a small script or test that validates README command table against registry metadata.

### Rationale

- Prevents documentation drift.
- Reduces update overhead when commands change.

### Detailed tasks

1. Add metadata fields and helper renderer.
2. Replace hard-coded help block with generated output.
3. Add doc-consistency test for core command docs.

## Recommendation 7: Tighten quality gates and static analysis coverage

### File references

- `pyproject.toml`
- `.github/workflows/*` (new)
- `README.md` (developer section)

### Current state

- Tests are strong, but static typing and linting gates are not enforced in workflow.
- Cross-platform behavior is not continuously validated in CI matrix.

### Proposed state

- Add project configs and CI checks for:
  - `ruff check`
  - `mypy src/tk`
  - `pytest`
- Add matrix for `ubuntu-latest`, `macos-latest`, and `windows-latest`.

### Rationale

- Prevents regressions from local-environment assumptions.
- Makes refactor work safer by enforcing contracts automatically.

### Detailed tasks

1. Add `mypy` and `ruff` config blocks in `pyproject.toml`.
2. Add CI workflow running lint/type/test across platforms.
3. Document local quality commands in README for contributors.

## Recommendation 8: Expand high-value temporal and integration tests

### File references

- `tests/test_subjective_date.py`
- `tests/test_profile.py`
- `tests/test_repl.py`
- `tests/test_commands.py`

### Current state

- Unit coverage is already strong, but temporal edge cases can still regress silently.
- Integration-level flows around parsing and date boundaries can be deepened.

### Proposed state

- Add focused test sets for:
  - DST boundaries and ambiguous local times.
  - Day-start boundary exact times (`==`, `<`, `>`).
  - Profile variations with path shortcuts across separators.
  - REPL parsing with quoted text and mixed flag patterns.

### Rationale

- Timezone/date logic is a long-term risk hotspot.
- Extra targeted tests preserve confidence during decomposition.

### Detailed tasks

1. Add parameterized DST/day-boundary test matrix.
2. Add parser edge-case integration tests.
3. Add regression tests for Windows-style shortcut normalization.

## Execution Plan (Task List)

1. Phase 1 foundation: implement models and adapters (Recommendation 1).
2. Phase 2 structure: split `data.py` and `commands.py` with compatibility shims (Recommendations 2 and 3).
3. Phase 3 reliability: introduce explicit exceptions and parser refactor (Recommendations 4 and 5).
4. Phase 4 consistency: metadata-driven help/docs validation (Recommendation 6).
5. Phase 5 enforcement: quality gates and CI matrix (Recommendation 7).
6. Phase 6 hardening: expand temporal/integration tests and remove migration shims (Recommendation 8).

## Validation Strategy

1. Run test suite after each phase.
2. Preserve command output snapshots for key REPL flows before/after refactor.
3. Run platform checks on macOS/Linux/Windows in CI before merging.
4. Keep JSON file format backward-compatible throughout.

## Definition of Done

- Modules are responsibility-focused and no longer rely on broad `dict[str, Any]` contracts for core entities.
- Help text and command metadata are synchronized by design.
- Error semantics are explicit and boundary handling is centralized.
- CI enforces lint, type, and test checks across all target platforms.
