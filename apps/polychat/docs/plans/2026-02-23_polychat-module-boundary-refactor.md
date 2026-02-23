# PolyChat Module Boundary Refactor Plan

Implementation plan generated on 2026-02-23.

## Objective

Improve maintainability by aligning module placement with responsibilities, reducing root-level coupling, and splitting oversized mixed-concern modules into focused packages.

## Scope

This plan is based on source-code structure and imports in:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat`
- `/Users/nao7sep/code/shared/apps/polychat/tests`

Non-source artifacts (except existing README/docs references for compatibility impact) are excluded from structural decisions.

## Baseline Architecture Snapshot (Current State)

1. No module import cycles were detected.
2. Several oversized modules still exceed the project split threshold:
   - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestrator.py` (~663 lines)
   - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/runtime.py` (~649 lines)
   - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/session_manager.py` (~645 lines)
   - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/metadata.py` (~519 lines)
   - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/ai/claude_provider.py` (~522 lines)
3. Root package (`polychat/*`) still contains multiple domain-heavy modules that would be clearer under subpackages (`ai`, `session`, `chat`, `formatting`, `repl`).
4. `models.py` and `costs.py` mix distinct concerns (catalog/capabilities/pricing vs estimation/presentation).

## Refactor Recommendations

### R1. Split `models.py` into AI catalog/capability/pricing modules

Files:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/models.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/costs.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/base.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/runtime.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/dispatcher.py`

Current state:
- `models.py` contains:
  - provider shortcuts and provider resolution
  - model registry and model search/fuzzy resolution
  - provider capability flags (`SEARCH_SUPPORTED_PROVIDERS`)
  - model pricing (`ModelPricing`, `MODEL_PRICING`)

Proposed state:
- Create:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/ai/catalog.py` (model registry + provider/model lookup)
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/ai/capabilities.py` (provider feature flags such as search support)
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/ai/pricing.py` (pricing table + `ModelPricing`)
- Keep `/Users/nao7sep/code/shared/apps/polychat/src/polychat/models.py` as a temporary compatibility facade that re-exports old names during migration.

Rationale:
- AI-specific concerns should live under `ai/` to reduce root-level sprawl.
- Smaller focused modules improve discoverability and reduce accidental cross-concern edits.

### R2. Separate cost domain logic from cost presentation

Files:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/costs.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/helper_ai.py`

Current state:
- `costs.py` contains both:
  - cost estimation domain logic (`estimate_cost`)
  - UI formatting (`format_cost_line`, `format_cost_usd`)

Proposed state:
- Move domain logic to:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/ai/costing.py`
- Move formatting to:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/formatting/costs.py`
- Keep `/Users/nao7sep/code/shared/apps/polychat/src/polychat/costs.py` as compatibility re-export until imports are migrated.

Rationale:
- Estimation logic belongs to AI billing domain; display text belongs to formatting/UI.
- This clarifies what can be reused in non-CLI contexts.

### R3. Decompose `orchestrator.py` by flow responsibility

Files:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestrator.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestrator_types.py`

Current state:
- Single class handles:
  - command signal routing
  - chat lifecycle transitions
  - message preparation per mode
  - response/error/cancel mutation handling
  - persistence coordination

Proposed state:
- Introduce package:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/`
  - `signals.py` (command signal handlers)
  - `message_entry.py` (normal/retry/secret message preparation)
  - `response_handlers.py` (success/error/cancel post-send behavior)
  - `chat_switching.py` (new/open/close/delete/rename state transitions)
- Keep `/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestrator.py` as thin facade/composer.

Rationale:
- Reduces the cognitive burden of one mega-orchestrator.
- Makes behavior tests map directly to modules.

### R4. Shrink `session_manager.py` into a true facade

Files:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/session_manager.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/app_state.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/session/*`

Current state:
- `SessionManager` has many concerns:
  - property accessors
  - chat lifecycle mutation
  - timeout state policy
  - retry/secret mode delegation
  - provider caching and switching
  - system prompt loading bridge

Proposed state:
- Keep `SessionManager` as facade only.
- Move state model and cache internals from root:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/app_state.py`
  - to `/Users/nao7sep/code/shared/apps/polychat/src/polychat/session/state.py`
- Add focused modules:
  - `session/chat_lifecycle.py`
  - `session/provider_cache.py`
  - `session/accessors.py`
- Preserve legacy imports with lightweight compatibility module(s).

Rationale:
- `session/` already exists and should own session concerns consistently.
- Facade-only manager is easier to maintain and type-check.

### R5. Split command runtime by command families

Files:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/runtime.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/metadata.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/registry.py`

Current state:
- `runtime.py` combines model/helper selection, mode toggles, system prompt path handling, rewind/purge destructive operations.
- `metadata.py` combines metadata generation and history/status rendering.

Proposed state:
- Replace two large mixins with family modules:
  - `commands/runtime_models.py`
  - `commands/runtime_modes.py`
  - `commands/runtime_mutation.py`
  - `commands/meta_generation.py`
  - `commands/meta_inspection.py`
- Keep registry/dispatcher stable and point to new handlers.

Rationale:
- Limits per-file blast radius and makes command behavior easier to locate.

### R6. Introduce `chat/` package and relocate chat modules

Files:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/chat.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/chat_manager.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/ui/chat_ui.py`

Current state:
- Chat storage/mutation (`chat.py`) and chat file listing/rename/delete (`chat_manager.py`) are separate root modules.

Proposed state:
- Create:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/chat/storage.py`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/chat/messages.py`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/chat/files.py`
- Keep `chat.py`/`chat_manager.py` as compatibility wrappers during migration.

Rationale:
- Consolidates chat domain in one directory and avoids root namespace crowding.

### R7. Split formatting concerns out of `text_formatting.py`

Files:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/text_formatting.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/metadata.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/ui/chat_ui.py`

Current state:
- One module handles:
  - text line normalization
  - truncation/minification
  - history render formatting
  - chat list formatting
  - citation formatting

Proposed state:
- Create:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/formatting/text.py`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/formatting/history.py`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/formatting/chat_list.py`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/formatting/citations.py`
- Leave `text_formatting.py` as migration facade.

Rationale:
- Improves cohesion and avoids unrelated edits colliding in one file.

### R8. Move runtime composition modules into feature packages

Files:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/ai_runtime.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/helper_ai.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl.py`

Current state:
- `ai_runtime.py` (provider init/send/validation) is root-level.
- `helper_ai.py` (helper request orchestration) is root-level.

Proposed state:
- Move to:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/ai/runtime.py`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/ai/helper_runtime.py`
- Keep root files as shims with deprecation comments.

Rationale:
- Runtime execution policy for AI belongs in `ai/`, not root.
- Makes provider stack easier to navigate.

### R9. Extract REPL internals into `repl/` package

Files:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/streaming.py`

Current state:
- `repl.py` owns loop lifecycle, keybindings, command execution, send pipeline, logging emission, and error paths.

Proposed state:
- Create:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl/loop.py`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl/input.py`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl/send_pipeline.py`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl/status_banners.py`
- Keep `/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl.py` as public API shim (`repl_loop` import).

Rationale:
- Keeps CLI loop thin and limits regression risk in send logic changes.

### R10. Rename ambiguous modules for intent clarity

Files:
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/setup.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/prompts.py`
- `/Users/nao7sep/code/shared/apps/polychat/src/polychat/logging_utils.py`

Current state:
- Some names are broad or potentially confusing:
  - `setup.py` (wizard, not packaging config)
  - `prompts.py` (template composition, not prompt resources)
  - `logging_utils.py` (currently a compatibility facade)

Proposed state:
- Rename and/or convert to explicit façade names:
  - `setup.py` -> `setup_wizard.py` (with `setup.py` shim)
  - `prompts.py` -> `prompt_templates.py` or `prompts/templates.py`
  - `logging_utils.py` remains temporarily for compatibility, with all logic in `logging/*`

Rationale:
- Better names reduce onboarding friction and accidental misuse.

## Directory Target State

Target package map (incremental):

- `polychat/ai/`
  - `runtime.py`, `helper_runtime.py`, `catalog.py`, `capabilities.py`, `pricing.py`, `costing.py`, provider modules
- `polychat/session/`
  - `state.py`, `accessors.py`, `chat_lifecycle.py`, `modes.py`, `messages.py`, `timeouts.py`, `system_prompt.py`, `provider_cache.py`
- `polychat/chat/`
  - `storage.py`, `messages.py`, `files.py`
- `polychat/commands/`
  - smaller handler family modules + existing dispatcher/registry
- `polychat/orchestration/`
  - signal/message/response handlers
- `polychat/repl/`
  - loop/input/send pipeline
- `polychat/formatting/`
  - text/history/chat_list/citations/costs

## Migration Strategy

1. Compatibility-first moves:
   - Introduce new modules, keep old root modules as re-export shims.
2. Import migration:
   - Update internal imports package-by-package (`ai`, `commands`, `repl`, `session`).
3. Test stabilization:
   - Ensure all tests pass after each phase.
4. Shim cleanup:
   - Remove shims only after full test migration and no in-repo imports remain.

## Tasklist (Phased)

### Phase 1: AI catalog/capability/pricing split

- [x] Add `ai/catalog.py`, `ai/capabilities.py`, `ai/pricing.py`, `ai/costing.py`.
- [x] Convert `models.py` and `costs.py` into compatibility re-export facades.
- [x] Update imports in command/repl/helper modules to new AI modules.
- [x] Update tests (`test_models.py`, `test_search_feature.py`, `test_costs.py`) for new primary import paths while preserving backward compatibility tests.

### Phase 2: Chat and session boundary alignment

- [ ] Introduce `chat/` package (`storage.py`, `messages.py`, `files.py`).
- [x] Move state internals from `app_state.py` to `session/state.py` and add shim.
- [x] Extract `session/chat_lifecycle.py` and `session/provider_cache.py`.
- [ ] Keep `session_manager.py` as facade, remove internal duplication.

### Phase 3: Orchestration and REPL decomposition

- [ ] Create `orchestration/` package and split current orchestrator responsibilities.
- [ ] Create `repl/` package (`loop.py`, `input.py`, `send_pipeline.py`, `status_banners.py`).
- [ ] Keep root `orchestrator.py` and `repl.py` as thin compatibility entry points.
- [ ] Add/adjust tests around send pipeline and mode transitions.

### Phase 4: Command module decomposition

- [ ] Split `commands/runtime.py` into focused runtime family modules.
- [ ] Split `commands/metadata.py` into generation vs inspection modules.
- [ ] Keep `commands/registry.py` as command source of truth.
- [ ] Ensure command help and behavior remain unchanged.

### Phase 5: Formatting extraction and naming cleanup

- [ ] Add `formatting/` package and move text/history/chat/citation/cost display formatters.
- [ ] Rename `setup.py` to `setup_wizard.py` with compatibility shim.
- [ ] Move `prompts.py` content to explicit template module path.
- [ ] Retain `logging_utils.py` as compatibility facade only.

### Phase 6: Cleanup and hardening

- [ ] Remove obsolete shims after all references are migrated.
- [ ] Run full test suite and static checks.
- [ ] Add architecture notes describing package ownership boundaries.

## Validation Gates Per Phase

- [ ] `cd /Users/nao7sep/code/shared/apps/polychat && .venv/bin/pytest -q`
- [ ] `cd /Users/nao7sep/code/shared/apps/polychat && .venv/bin/ruff check src tests`
- [ ] `cd /Users/nao7sep/code/shared/apps/polychat && mypy src/polychat` (or scoped package checks during migration)

## Risks and Mitigations

1. Risk: Import churn causes breakage.
   - Mitigation: Introduce compatibility shims first, migrate in narrow phases.
2. Risk: Behavior regressions in retry/secret/search flows.
   - Mitigation: Expand orchestration behavior tests before deep split.
3. Risk: Test fragility from module path changes.
   - Mitigation: Keep old import paths valid until final cleanup.

## Exit Criteria

- Root-level modules are thin entry points or facades, not mixed-concern implementations.
- AI, session, chat, orchestration, REPL, and formatting concerns are placed in corresponding directories.
- No oversized mixed-responsibility modules remain above maintainability threshold.
- All tests and lint/type checks pass after migration.
