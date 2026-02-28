# Code Review: Dict-to-Model Migration

**Commit:** `843cf369b646ef3f77aac1683dd60cdb83d46359` — "Refactor tests to use Task and TaskStore models"
**Scope:** `apps/tk/` source and tests only
**Date:** 2026-02-28

## Summary

This commit removes all dict-like compatibility shims (`__getitem__`, `__setitem__`, `get`, `keys`, `__contains__`) from every model dataclass (`Task`, `TaskStore`, `Profile`, `TaskListItem`, `PendingListPayload`, `HistoryFilters`, `HistoryGroup`, `HistoryListPayload`) and migrates all call sites — source and tests — to direct attribute access.

Two new dataclasses are introduced:

- `DoneCancelResult` — replaces the ad-hoc dict returned by `collect_done_cancel_prompts`
- `CommandDocEntry` — replaces `dict[str, str]` in the dispatcher help/doc system

The commit also:

- Makes `create_profile` return a `Profile` with mapped absolute paths directly, eliminating the redundant `load_profile` call in the `init` flow
- Removes the `dict[str, Any]` union from `Session.profile` and `Session.tasks`, along with the auto-conversion fallbacks in `require_profile` / `require_tasks`
- Simplifies `extract_last_list_mapping` by removing dict fallback branches
- Cleans up `repl.py`: removes dead `pass` statement, replaces duck-typed `sync_on_exit` path with clean attribute access, adds `noqa: F401` to the `readline` side-effect import

All test files are migrated from dict-based fixtures and assertions to model-based equivalents.

## Separation of Concerns

No issues. The layer boundaries (models, storage, data API, commands, REPL, prompts, formatters) remain intact. The migration tightens these boundaries by replacing `dict[str, Any]` parameters with concrete types, making cross-layer contracts explicit.

## Correctness

No bugs found. Specific areas verified:

- **`TaskStore.update_task` field-setting logic:** The inline `if/elif/else` chain is equivalent to the removed `Task.__setitem__`, correctly coercing status via `_coerce_task_status`, handling nullable optional fields, and falling through to `str(value)` for `text`.
- **`create_profile` path mapping:** Absolute paths are mapped *after* writing the file (so the persisted JSON retains relative paths), matching `load_profile` behavior.
- **`extract_last_list_mapping`:** The removed dict fallback branches were unreachable since all callers already produce typed payloads.
- **`repl.py` sync_on_exit:** `profile_data.sync_on_exit` correctly replaces `profile_data.get("sync_on_exit", False)` because `Profile` defaults `sync_on_exit` to `False`.
- **Sort keys:** `t.created_utc` (no fallback) is safe because `created_utc` is a required field validated in `Task.from_dict`. `t.handled_utc or ""` correctly handles `None` for optional timestamps.

## Error Handling

No issues. Exception paths remain unchanged. All CRUD methods still raise `ValueError` for invalid fields/indices, caught at the REPL boundary.

## Security

No issues. No user-controlled paths, shell commands, or credential handling was affected by this commit.

## Findings

### F1 — Missing type annotations in `data.py`

**Severity:** Minor
**File:** `apps/tk/src/tk/data.py`, lines 17 and 22

`get_task_by_index` has no return type annotation. `update_task` has untyped `**updates`. Since the underlying `TaskStore` methods are fully typed, mypy will infer `Any` at this module boundary, silently defeating the typed-model migration that this commit is completing.

```python
# current
def get_task_by_index(tasks_data: TaskStore, index: int):
def update_task(tasks_data: TaskStore, index: int, **updates) -> bool:

# suggested
def get_task_by_index(tasks_data: TaskStore, index: int) -> Task | None:
def update_task(tasks_data: TaskStore, index: int, **updates: Any) -> bool:
```

### F2 — `_serialize_tasks` name is misleading after migration

**Severity:** Minor
**File:** `apps/tk/src/tk/commands.py`, line 27

`_serialize_tasks` previously converted tasks to dicts (`[task.to_dict() for task in ...]`). It now returns `tasks_data.tasks` directly — no serialization occurs. The name is misleading. Consider renaming to `_task_list` or inlining the `.tasks` access at the two call sites (lines 38 and 321).

### F3 — `_serialize_tasks` returns mutable internal reference

**Severity:** Minor
**File:** `apps/tk/src/tk/commands.py`, line 29

The returned `list[Task]` is the same object held by `TaskStore.tasks`. Not a bug today — `generate_todo` only reads — but a latent mutation risk if a future caller modifies the returned list. A shallow copy (`list(tasks_data.tasks)`) or inlining would eliminate the risk.

All three findings are quick fixes.
