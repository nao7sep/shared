# PolyChat Facade Boundary Cleanup Plan

## Scope

- App: `/Users/nao7sep/code/shared/apps/polychat`
- Goal: improve structural maintainability by reducing compatibility-facade coupling inside feature packages.
- Out of scope: behavior changes, feature additions, provider/model logic changes.

## Why This Refactor Now

The current codebase is already mostly well-separated by package (`ai`, `chat`, `session`, `commands`, `orchestration`, `repl`).

Non-minor maintainability drag remains in a few high-traffic paths where feature modules still route calls through root compatibility facades. This creates indirect dependency paths that are harder to reason about and makes boundary regressions easier.

## Recommendation 1: Remove Orchestration Backreferences To Root `orchestrator`

### Current State

`orchestration/*` handlers late-import root `orchestrator` and then call chat APIs through `orchestrator_module.chat`:

- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/message_entry.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/chat_switching.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/response_handlers.py`

This introduces an avoidable feature -> root facade -> feature indirection path.

### Proposed State

- Replace late imports with direct feature-package imports from `polychat.chat` (or narrower submodules if preferred).
- Keep `src/polychat/orchestrator.py` as a thin composition facade only.
- Update tests that currently patch old paths to patch direct feature-level imports.

### Rationale

Responsibilities are currently mixed between:

1. Orchestration state transitions.
2. Compatibility patch seams tied to root facade import paths.

These have independent reasons to change. Removing the seam from feature handlers simplifies dependency flow and preserves the root facade’s intended role.

## Recommendation 2: Remove Metadata Generation Backreference To Root `commands`

### Current State

`meta_generation.py` late-imports root `commands` and calls `commands_module.invoke_helper_ai` via re-export:

- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/meta_generation.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/__init__.py`

### Proposed State

- Inject helper invocation dependency explicitly into command handlers (for example through `CommandContext` or handler constructor wiring).
- Call `ai.helper_runtime.invoke_helper_ai` through that injected dependency, not via root `commands` re-export.
- Keep re-export only if strictly required for external compatibility; remove internal usage.

### Rationale

Responsibilities are currently mixed between:

1. Metadata generation behavior.
2. Compatibility import indirection for test patching.

These should be decoupled so command internals depend on explicit runtime contracts instead of package-level facades.

## Recommendation 3: Centralize Command Output Side Effects Behind Interaction Port

### Current State

Some command handlers print directly to stdout for warnings/confirm flows:

- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/runtime_mutation.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/chat_files.py`

Other interaction paths already go through `UserInteractionPort`.

### Proposed State

- Extend interaction abstraction with an output method for non-return-value notices (or convert warnings into structured return values consistently).
- Replace direct `print()` in command handlers with the unified output pathway.
- Keep visible CLI behavior unchanged.

### Rationale

Responsibilities are currently mixed between:

1. Command-domain mutation logic.
2. Console rendering side effects.

Separating these improves testability and keeps the command layer UI-agnostic.

## Recommendation 4 (Lower Priority): Move System Prompt File-Loading Out of Session Operations

### Current State

`session/operations.py` includes session-mode/state operations and also prompt/profile file I/O in `load_system_prompt`.

- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/session/operations.py`

### Proposed State

- Move system prompt resolution/loading into a dedicated prompt/profile-facing module.
- Keep `SessionManager.load_system_prompt(...)` API stable as a facade entry point.

### Rationale

Responsibilities are currently mixed between:

1. In-memory session state transitions.
2. External file resolution/loading policy.

Separation will reduce churn in session module for prompt policy changes.

## Execution Plan

1. Add a boundary test to block feature modules from importing root facades (except explicitly allowed shims).
2. Refactor orchestration modules to use direct chat feature imports.
3. Refactor metadata generation helper invocation to explicit dependency wiring.
4. Unify command-side output through interaction abstraction.
5. (Optional) extract system prompt loading from `session/operations.py`.
6. Run full test suite and update architecture docs if boundary rules are tightened.

## Validation

- Existing behavior tests remain green.
- New boundary test prevents regressions.
- No feature package requires root facade imports for internal behavior.
- CLI-visible output and command semantics remain unchanged.
