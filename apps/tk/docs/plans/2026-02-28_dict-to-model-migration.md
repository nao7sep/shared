# tk Dict-to-Model Migration

Implementation plan generated from conversation on 2026-02-28.

## Overview

Complete the migration from raw `dict[str, Any]` usage to the typed dataclass models (`Task`, `TaskStore`, `Profile`) that already exist in `models.py`. The codebase is mid-migration: models are defined and have dict-like shims (`__getitem__`, `get`, etc.) for backward compatibility, but many call sites still pass and accept raw dicts. This violates the playbook rule: "Never use raw dicts for structured data."

## Requirements

### Storage layer

- `storage.load_tasks()` must return `TaskStore` (not `dict[str, Any]`).
- `storage.save_tasks()` must accept `TaskStore` (not `dict[str, Any] | Any`).
- `storage.validate_tasks_structure()` remains as-is — it validates raw JSON dicts before conversion.

### Profile layer

- `profile.load_profile()` must return `Profile` (not `dict[str, Any]`).
- `profile.create_profile()` must return `Profile` (not `dict[str, Any]`). The raw dict written to JSON is fine as a local variable; the return type must be `Profile`.
- `profile.validate_profile()` continues to accept `dict[str, Any]` — it validates raw JSON before conversion.

### Data API layer

- Remove all dual-path `dict[str, Any] | Any` signatures and dict fallback code paths from `data.py`. Every function should accept `TaskStore` directly.
- Remove the standalone `add_task`, `get_task_by_index`, `update_task`, `delete_task` wrappers — callers should use `TaskStore` methods directly.
- Keep `data.py` as the re-export surface for `load_tasks`, `save_tasks`, `group_tasks_for_display`, `group_handled_tasks`.

### Query layer

- `task_queries.group_tasks_for_display()` must accept `list[Task]` (not `list[Any]`).
- `task_queries.group_handled_tasks()` must accept `list[tuple[int, Task]]` (not `list[tuple[int, Any]]`).

### Markdown layer

- `markdown.generate_todo()` must accept `list[Task]` (not `list[dict[str, Any]]`).

### Prompts layer

- `prompts.collect_done_cancel_prompts()` must accept `task: Task` (not `dict[str, Any]`).
- The return value `{"note": ..., "date": ...}` must become a `DoneCancelResult` dataclass.
- `prompts.collect_delete_confirmation()` must accept `task: Task` (not `dict[str, Any]`).

### Dispatcher layer

- `dispatcher.command_doc_entries()` must return `list[CommandDocEntry]` where `CommandDocEntry` is a new dataclass with fields: `command`, `alias`, `usage`, `summary`, `display_usage`.

### Session layer

- `Session.profile` type annotation must be `Profile | None` (not `Profile | dict[str, Any] | None`).
- `Session.tasks` type annotation must be `TaskStore | None` (not `TaskStore | dict[str, Any] | None`).
- Remove the `isinstance(self.profile, dict)` / `isinstance(self.tasks, dict)` lazy-conversion branches in `require_profile()` / `require_tasks()`.

### CLI bootstrap

- `cli.py` init path must use `TaskStore()` instead of `{"tasks": []}`.
- `cli.py` must work with `Profile` objects (not dicts) after `load_profile()`.
- `display_profile_info()` must accept `Profile` (not `dict`).

### REPL exit handler

- `repl.py` exit sync path (lines 193-198) must use model attribute access instead of dict access and `hasattr` checks.

### Model cleanup

- Remove dict-like shims (`__getitem__`, `__setitem__`, `get`, `keys`, `__contains__`) from `Task`, `TaskStore`, `Profile`, `TaskListItem`, `PendingListPayload`, `HistoryFilters`, `HistoryGroup`, `HistoryListPayload` once no call site uses dict-style access.

## Architecture

No architectural changes. The module structure stays the same:

```
storage.py       → JSON I/O (dict ↔ file), returns models
profile.py       → Profile I/O, validation, path mapping, returns Profile
data.py          → Re-exports storage + query functions
models.py        → All dataclass models (Task, TaskStore, Profile, payloads, + new DTOs)
task_queries.py  → Grouping/sorting helpers, typed with Task
markdown.py      → TODO.md generation, typed with Task
prompts.py       → Interactive input collection, typed with Task + DoneCancelResult
commands.py      → Business logic (already mostly correct)
dispatcher.py    → Command routing + CommandDocEntry model
session.py       → Runtime state, strict model types
cli.py           → Bootstrap
repl.py          → REPL loop
```

New models to add in `models.py`:
- `DoneCancelResult(note: str | None, date: str)` — replaces the `{"note": ..., "date": ...}` dict in `prompts.py`.
- `CommandDocEntry(command: str, alias: str, usage: str, summary: str, display_usage: str)` — replaces the `dict[str, str]` in `dispatcher.py`.

## Implementation Steps

1. **Add new models.** Add `DoneCancelResult` and `CommandDocEntry` dataclasses to `models.py`.

2. **Migrate `storage.load_tasks()`.** Change return type from `dict[str, Any]` to `TaskStore`. Validate the raw JSON dict, then convert to `TaskStore.from_dict()` before returning. Update `save_tasks()` to accept `TaskStore` and call `.to_dict()` internally.

3. **Migrate `profile.load_profile()` and `create_profile()`.** Change return types to `Profile`. In `load_profile()`, validate the raw dict, apply path mapping, then return `Profile.from_dict()`. In `create_profile()`, build the raw dict for JSON serialization, then return `Profile.from_dict()` of the saved data (with mapped paths). Note: `Profile.from_dict()` does not currently map paths — path mapping must happen before conversion, on the raw dict side, or `Profile` must accept already-mapped paths (current approach is fine: map paths on raw dict, then convert).

4. **Migrate `session.py`.** Narrow type annotations to `Profile | None` and `TaskStore | None`. Remove the `isinstance(..., dict)` lazy-conversion branches.

5. **Migrate `cli.py`.** Update `display_profile_info()` to accept `Profile`. Update init path to use `TaskStore()` instead of `{"tasks": []}`. Use attribute access throughout.

6. **Migrate `prompts.py`.** Change `task` parameter types to `Task`. Change `collect_done_cancel_prompts()` return type to `DoneCancelResult | str`. Update `repl.py` to use `DoneCancelResult` attributes instead of dict-style `kwargs.update(result)`.

7. **Migrate `task_queries.py`.** Change parameter types to `list[Task]` and `list[tuple[int, Task]]`. Replace dict-style `task["status"]` / `task.get(...)` with attribute access.

8. **Migrate `markdown.py`.** Change `tasks` parameter to `list[Task]`. Replace dict-style access with attribute access. Update `commands.py` call sites that pass `_serialize_tasks()` — pass `tasks_data.tasks` directly instead.

9. **Migrate `dispatcher.py`.** Change `command_doc_entries()` to return `list[CommandDocEntry]`. Update `render_help_text()` to use attribute access.

10. **Simplify `data.py`.** Remove `_tasks_list()`, `add_task()`, `get_task_by_index()`, `update_task()`, `delete_task()` wrappers. Keep re-exports of `load_tasks`, `save_tasks`, `group_tasks_for_display`, `group_handled_tasks`. Verify no external callers depend on the removed functions.

11. **Migrate `repl.py` exit handler.** Replace `profile_data.get("sync_on_exit", False)` and dict-style task access with model attribute access.

12. **Remove dict-like shims from models.** Delete `__getitem__`, `__setitem__`, `get`, `keys`, `__contains__` from all dataclasses in `models.py`. Remove `_TASK_FIELDS` and `_PROFILE_FIELDS` tuples if no longer referenced.

13. **Update tests.** Fix any tests that construct raw dicts where models are now expected. Tests in `conftest.py` and individual test files may need to use `Task(...)`, `TaskStore(...)`, `Profile(...)` constructors instead of dict literals.

14. **Run `ruff`, `mypy`, and `pytest`.** Verify no lint errors, type errors, or test failures.

## Open Questions

- **`commands.py:extract_last_list_mapping()`** currently accepts `dict[str, Any]` as a third union branch for backward compatibility. After migration, is there any remaining caller that passes a raw dict? If not, the dict branch can be removed.
- **`data.py` as re-export surface.** After removing the wrapper functions, `data.py` becomes a thin re-export module. Should it be kept for import convenience, or should callers import directly from `storage` and `task_queries`?
