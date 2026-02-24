# PolyChat Save Policy and `updated_at` Refactor Plan (2026-02-24)

## Goal

Implement two behavior corrections together:

1. Adjust `updated_at` timing so read-only/runtime-only commands do not update chat file timestamps.
2. Remove legacy "dirty chat" language/concept while keeping immediate-save UX (no deferred mode, no `/save` command).

## Current State (Evidence)

- Command string responses trigger persistence unconditionally:
  - `src/polychat/orchestrator.py`
  - `src/polychat/orchestration/signals.py`
- Session-level save helper is unconditional (except missing path/data), so timestamp churn follows any command-driven save attempt:
  - `src/polychat/session/operations.py`
- Chat storage always touches `metadata.updated_at` on write:
  - `src/polychat/chat/storage.py`
- Read-only/runtime-only commands currently return plain strings and are indistinguishable from mutating command responses at orchestration save boundary:
  - `src/polychat/commands/runtime_modes.py`
  - `src/polychat/commands/meta_inspection.py`
  - `src/polychat/commands/misc.py`

## Proposed State

### 1) Keep immediate-save flow, but make writes idempotent when persisted payload is unchanged

- Update chat storage save path to compare normalized persistable payload against existing on-disk payload before writing.
- Skip file write and timestamp mutation when there is no persisted change.
- Continue writing immediately when content/metadata actually changes.

Files:
- `src/polychat/chat/storage.py`
- `tests/test_chat.py`

Rationale:
- This preserves current UX (save immediately) while fixing timestamp churn from no-op saves.

### 2) Remove residual "dirty chat" terminology completely

- Keep neutral naming in orchestrator/signal helpers.
- Ensure comments/docstrings reflect immediate-save + no-op-write semantics (not "dirty state" semantics).

Files:
- `src/polychat/orchestrator.py`
- `src/polychat/orchestration/signals.py`

Rationale:
- Removes misleading language and aligns implementation docs with actual behavior.

### 3) Add command-level regression coverage for `updated_at` timing

- Add integration tests covering representative runtime-only commands (`/search`, `/retry`, `/help`) showing no `updated_at` bump without persisted chat mutations.
- Add mutation-path coverage (`/title`, `/summary`, `/rewind`, `/purge`, `/apply`) showing timestamp changes only when persisted payload differs.

Files:
- `tests/test_orchestrator.py` (or dedicated timestamp behavior test module)

Rationale:
- Locks in expected behavior where command handling remains immediate but idempotent for no-op paths.

## Task List

- [x] Implement idempotent save behavior in chat storage (skip no-op writes).
- [x] Confirm and finalize removal of legacy "dirty chat" wording.
- [x] Update/expand tests for timestamp behavior across read-only/runtime-only vs mutating command flows.
- [x] Run validation (`ruff`, `mypy`, targeted pytest, then full pytest if green).

## Validation Plan

- Behavior checks:
  - `/search`, `/retry`, `/help`, `/history`, `/show`, `/status` do not bump `updated_at`.
  - `/title`, `/summary`, `/system`, `/rewind`, `/purge`, `/apply` bump `updated_at` only when a write actually occurs.
- Test/lint/type gates:
  - `ruff check src tests`
  - `mypy src/polychat`
  - targeted pytest for orchestrator/commands/profile/chat
  - full `pytest -q`

## Completion Update (2026-02-24)

- Implemented no-op write detection in `src/polychat/chat/storage.py`.
  - Save now compares normalized persistable payload against on-disk payload and skips writing when unchanged.
  - `updated_at` only moves forward when persisted content/metadata changes.
- Confirmed neutral naming for command-response persistence helper:
  - `src/polychat/orchestrator.py`
  - `src/polychat/orchestration/signals.py`
- Updated timestamp tests in `tests/test_chat.py` to assert no timestamp bump for unchanged payload and bump on actual mutation.
- Added integration command-flow coverage in `tests/test_updated_at_behavior.py`:
  - runtime-only commands do not bump `updated_at`
  - mutating commands bump `updated_at` only on real changes
- Validation:
  - `ruff check src tests` passed
  - `.venv/bin/mypy src/polychat` passed
  - focused pytest suites passed
  - full test suite passed: `577 passed, 3 deselected, 1 warning`
