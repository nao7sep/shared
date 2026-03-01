# Retry/Secret Implementation Plan

Date: 2026-03-01

Context: Implement `/retry` and `/secret` so runtime behavior matches [`docs/architecture/retry-and-secret-modes.md`](/Users/nao7sep/code/shared/apps/polychat/docs/architecture/retry-and-secret-modes.md).

## Goal

Make the code match the clarified architecture:

- `/retry` = ephemeral replacement branch for the last interaction
- `/secret` = ephemeral continuation branch after the committed chat

This plan is intentionally narrow. It targets mode semantics, state handling, and failure shapes required by those semantics. It does not attempt broader cleanup unless that cleanup is necessary to make the modes correct.

## Target Behavior

### Retry

- The target is always the current last interaction.
- The last interaction may be:
  - trailing `user + assistant`
  - trailing `user + error`
  - standalone trailing `error`
- Retry attempts send only the committed prefix before the target plus a new retry user message.
- The original target interaction is never sent to the AI during retry attempts.
- Multiple retry attempts may be accumulated.
- `/apply` replaces the target interaction atomically.
- `/cancel` exits retry mode without changing committed history.

### Secret

- Secret mode starts from the committed chat at the moment `/secret on` is entered.
- Secret turns accumulate in an in-memory secret transcript.
- Each later secret turn uses:
  - committed base
  - prior secret transcript
  - new secret user message
- No secret message or secret error is written to committed chat or file.
- `/secret off` discards the entire secret transcript.
- The next normal committed message resumes from the durable chat, not from secret turns.

## Scope

### In Scope

- runtime state for retry and secret modes
- interaction-shape detection for last interaction
- normal-mode failure handling only where needed to make retry target shapes real
- send/error/cancel behavior for retry and secret
- command text and user guidance for these modes
- tests covering the clarified contract

### Out Of Scope

- broad persistence transaction refactors outside mode-specific code
- command-system redesign
- unrelated architecture cleanup
- UI redesign beyond wording and mode semantics

## Current Gaps

### Retry Gaps

Retry is already close to the target contract, but not fully codified:

- The target-shape rules are implicit and spread across helpers.
- The user-facing wording still partially describes retry as replaying the same message.
- Standalone-error replacement currently produces a new user message with no runtime hex ID.
- The normal failure model does not yet intentionally produce both `u+e` and standalone `e` shapes in a controlled way.

### Secret Gaps

Secret does not currently behave like a growing off-the-record branch:

- `SecretController` stores only a base snapshot.
- secret sends rebuild context from committed chat only.
- successful secret turns are not appended to any secret transcript.
- secret failures are not represented as secret-branch state.
- leaving secret mode clears state, but there is almost no secret state to clear.

## Design Decisions To Lock Before Editing

These decisions should be treated as implementation rules for this change:

1. Retry target selection uses the last interaction only.
2. Retry target shapes are exactly:
   - `user + assistant`
   - `user + error`
   - standalone `error`
3. Secret mode uses a frozen committed base captured at `/secret on`, not a dynamic view of later committed changes.
4. Secret transcript is runtime-only and never persisted.
5. Normal-mode failures must intentionally produce:
   - `user + error` when the user turn is part of the failed committed interaction
   - standalone `error` when failure occurs before there is a durable user turn for that interaction
6. Retry apply must preserve or assign runtime hex IDs so every committed message remains addressable after replacement.

## Workstream 1: Centralize Interaction-Shape Logic

### Objective

Remove implicit shape assumptions and replace them with one explicit interaction model used by retry, rewind, and failure handling.

### Changes

Add a small typed interaction helper layer, likely in `src/polychat/chat/messages.py` or a new focused module under `src/polychat/orchestration/`:

- `LastInteractionKind`
  - `user_assistant`
  - `user_error`
  - `standalone_error`
- `LastInteractionSpan`
  - `replace_start`
  - `replace_end`
  - `context_end_exclusive`
  - `kind`

### Expected Use Sites

- [`src/polychat/commands/runtime_modes.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/runtime_modes.py)
- [`src/polychat/orchestration/signals.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/signals.py)
- [`src/polychat/commands/runtime_mutation.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/runtime_mutation.py)
- possibly [`src/polychat/session/state.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/session/state.py) if pending-error wording/logic is derived from shape

### Why First

Retry and rewind already encode overlapping “last interaction” rules. Secret and normal error handling also need a shared view of what the last interaction means. Centralizing this first reduces follow-on churn.

## Workstream 2: Make The Normal Failure Model Explicit

### Objective

Make committed error shapes intentional instead of incidental, because retry depends on those shapes.

### Required Outcome

There must be a clear separation between:

- pre-commit / preflight failure -> standalone `eN`
- post-user-turn failure -> durable `uN + eN`

### Recommended Rule

Use the failure phase already visible in the send pipeline:

- provider-resolution / preflight failures before a committed interaction is finalized:
  - persist standalone `error`
- failures after a normal user turn is already the basis of the attempted interaction:
  - keep the user message
  - append `error`

### Files

- [`src/polychat/repl/send_pipeline.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl/send_pipeline.py)
- [`src/polychat/orchestration/response_handlers.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/response_handlers.py)
- possibly [`src/polychat/orchestrator.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestrator.py) only if method boundaries need adjustment

### Notes

The current `rollback_pre_send_failure()` path removes the pending user turn and persists nothing. To make standalone `eN` real, that path likely needs a sibling flow that:

- removes any pending user turn if present
- appends an `error` message
- saves the chat

The current `handle_ai_error()` path removes the user turn before appending the error. That must change for the `u+e` case.

## Workstream 3: Codify Retry As Replacement-Branch Semantics

### Objective

Leave retry’s overall structure in place, but make it explicitly match the architecture.

### Changes

1. Enter retry mode using the centralized last-interaction helper rather than implicit tail-role checks.
2. Store the exact replacement span when entering retry mode, not just `target_index`.
3. Keep retry attempts as:
   - new retry user text
   - candidate assistant response
4. Apply using the stored replacement span.
5. Ensure replacement preserves message addressability:
   - `u+a` target:
     - preserve existing user hex ID
     - preserve existing assistant hex ID
   - `u+e` target:
     - preserve existing user hex ID
     - preserve existing error-slot hex ID on the new assistant message
   - standalone `e` target:
     - generate a new hex ID for the inserted user message
     - preserve or intentionally replace the old error hex ID for the inserted assistant message

### Files

- [`src/polychat/commands/runtime_modes.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/runtime_modes.py)
- [`src/polychat/session/retry_controller.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/session/retry_controller.py)
- [`src/polychat/orchestration/signals.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/signals.py)
- [`src/polychat/hex_id.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/hex_id.py) only if a helper is needed

### Suggested Internal Change

Upgrade retry state from:

- `base_messages`
- `target_index`

to:

- `base_messages`
- `replace_start`
- `replace_end`
- `target_kind`

This removes the need to recompute replacement rules during `/apply`.

## Workstream 4: Implement Secret As A Growing Runtime Branch

### Objective

Make secret mode maintain its own ephemeral transcript across multiple turns.

### Required State

Extend `SecretController` to hold:

- `base_messages`
- `secret_messages`
- `active`

Add methods such as:

- `enter(base_messages)`
- `exit()`
- `get_context()` -> `base_messages + secret_messages`
- `append_success(user_text, assistant_text, model, citations)`
- `append_error(...)`

### Behavior

On `/secret on`:

- capture committed `user`/`assistant` history as the frozen base
- clear any prior secret transcript

On each secret send:

- build AI context from `secret.get_context()` plus the new user message

On successful secret response:

- append the secret user message and assistant message to the secret transcript

On secret error:

- append secret error state to the secret transcript according to the same failure-shape policy used in normal mode
- never persist it to committed chat

On `/secret off`:

- clear the secret transcript completely

### Files

- [`src/polychat/session/secret_controller.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/session/secret_controller.py)
- [`src/polychat/orchestration/message_entry.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/message_entry.py)
- [`src/polychat/orchestration/response_handlers.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/response_handlers.py)
- [`src/polychat/commands/runtime_modes.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/runtime_modes.py)

### Important Test Correction

The current test that secret mode should follow later committed chat mutations after entry no longer matches the intended architecture. Replace that expectation with:

- base committed history is frozen at `/secret on`
- only secret transcript growth changes later secret context

## Workstream 5: Align Cancel/Error Semantics For Secret And Retry

### Retry

No committed mutation should occur for:

- failed retry attempts
- cancelled retry attempts

Existing attempts should remain available unless the retry state is explicitly cleared or invalidated.

### Secret

No committed mutation should occur for:

- successful secret turns
- failed secret turns
- cancelled secret turns

Recommended cancel behavior:

- if the user cancels a secret streamed response, do not append a partial secret turn
- leave the existing secret transcript unchanged

### Files

- [`src/polychat/orchestration/response_handlers.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/response_handlers.py)
- [`src/polychat/repl/send_pipeline.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/repl/send_pipeline.py)

## Workstream 6: Update User-Facing Wording

### Retry Wording Changes

Remove phrasing that implies automatic replay of the same prompt unless the implementation truly does that.

Update:

- pending error guidance
- help/command docs
- README wording if generated from command docs

Recommended phrasing:

- "Retry the last interaction by generating replacement candidate pairs"
- "Use /apply to replace the last interaction"

### Secret Wording Changes

Clarify that secret mode is multi-turn and contextual, not one unsaved one-shot message.

Recommended phrasing:

- "Continue off the record"
- "Secret turns affect later secret context until secret mode is turned off"

### Files

- [`src/polychat/session/state.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/session/state.py)
- [`src/polychat/commands/command_docs_data.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/command_docs_data.py)
- generated README content if applicable

## Workstream 7: Test Matrix

### New/Updated Retry Tests

Add or update tests for:

1. entering retry on trailing `u+a`
2. entering retry on trailing `u+e`
3. entering retry on trailing standalone `e`
4. retry context excludes the target interaction in all three shapes
5. multiple retry attempts accumulate
6. `/apply` on `u+a` preserves stable hex IDs
7. `/apply` on `u+e` preserves stable hex IDs
8. `/apply` on standalone `e` assigns a valid new user hex ID
9. `/cancel` leaves committed history unchanged

### New/Updated Secret Tests

Add or update tests for:

1. first secret turn uses committed base only
2. second secret turn includes prior secret `u+a`
3. successful secret turns do not mutate committed chat
4. successful secret turns do not trigger save
5. secret error does not mutate committed chat
6. `/secret off` clears the secret transcript
7. the first normal turn after `/secret off` resumes from committed history
8. secret mode does not pick up external committed mutations after entry

### Error-Shape Tests

Add focused orchestration tests for:

1. preflight failure persists standalone `e`
2. post-user-turn failure persists `u+e`
3. retry can target both resulting shapes correctly

### Likely Test Files

- [`tests/test_commands_runtime.py`](/Users/nao7sep/code/shared/apps/polychat/tests/test_commands_runtime.py)
- [`tests/test_orchestrator.py`](/Users/nao7sep/code/shared/apps/polychat/tests/test_orchestrator.py)
- [`tests/test_orchestration_mode_invariants.py`](/Users/nao7sep/code/shared/apps/polychat/tests/test_orchestration_mode_invariants.py)
- [`tests/test_orchestration_retry_transitions.py`](/Users/nao7sep/code/shared/apps/polychat/tests/test_orchestration_retry_transitions.py)
- [`tests/test_session_manager.py`](/Users/nao7sep/code/shared/apps/polychat/tests/test_session_manager.py)
- add a dedicated `tests/test_secret_mode_branching.py` if coverage becomes hard to read in the existing files

## Recommended Execution Order

### Phase 1: Lock Helper Model

- add centralized last-interaction/span helper
- add tests for interaction classification only

### Phase 2: Align Failure Shapes

- refactor normal send failure paths to intentionally produce `u+e` or `e`
- add tests for those two shapes

### Phase 3: Finish Retry

- refactor retry to use explicit span state
- fix standalone-error apply hex-ID assignment
- update retry wording
- update retry tests

### Phase 4: Build Secret Transcript

- extend `SecretController`
- route secret sends through `secret.get_context()`
- append successful secret turns into secret runtime state
- add secret branching tests

### Phase 5: Secret Error/Cancel Behavior

- implement secret-only error and cancel handling
- verify no committed mutation or save occurs

### Phase 6: Final Docs And Regression Pass

- align command docs and runtime guidance text
- run focused tests first
- then run full `uv run pytest -q`

## Risks

### Risk 1: Breaking Existing Retry Apply Semantics

Mitigation:

- refactor around explicit replacement spans
- keep apply behavior covered with before/after transcript assertions

### Risk 2: Secret Transcript Leaking Into Committed Chat

Mitigation:

- keep all secret mutation methods inside `SecretController`
- assert `save_current_chat` is never awaited on secret success/error/cancel paths

### Risk 3: Ambiguous Failure-Phase Boundaries

Mitigation:

- encode the rule in one place in the send/orchestrator layer
- test both preflight and post-user-turn failures explicitly

### Risk 4: Hex ID Regressions After Replacement

Mitigation:

- add targeted tests around `build_retry_replacement_plan`
- add a post-apply assertion that every committed message has the expected runtime hex-ID state

## Non-Goals For This Change

Do not mix this implementation with:

- the broader command persistence transaction refactor
- unrelated session-manager decomposition
- non-mode cleanup in the command system

Those are valid follow-ups, but mixing them into this change will make it harder to prove that mode semantics were fixed correctly.

## Definition Of Done

This work is done when all of the following are true:

1. `/retry` behaves as a replacement branch for all three last-interaction shapes.
2. `/secret` behaves as a multi-turn off-the-record continuation branch.
3. No secret turn or secret error is ever persisted.
4. Retry apply produces a valid committed transcript with correct runtime message addressability.
5. User-facing wording matches the implemented semantics.
6. The full test suite passes.
