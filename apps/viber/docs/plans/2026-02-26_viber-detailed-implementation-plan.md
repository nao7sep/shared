# Viber — Detailed Implementation Plan

Generated 2026-02-26. This document supersedes the initial design plan and includes all
decisions resolved in the follow-up design session. It is a complete, self-contained blueprint
for implementing viber from scratch.

---

## Overview

Viber is a local Python REPL app for managing repeated cross-project maintenance tasks.
Users define project groups, register projects (one group per project), add tasks that apply
to one group or all groups, and track per-project task assignments as `pending`, `ok`, or
`nah`. The tool optionally generates per-group HTML check pages so users can quickly see
maintenance state across many projects.

**App purpose:** Maintain vibe-coding speed and quality with minimal overhead for repetitive
maintenance checks.

---

## Resolved Decisions

| Topic | Decision |
|---|---|
| `--check` default | Disabled unless explicitly provided; no HTML generated when omitted |
| No-pending message | "Vibe is good. No pending assignments." |
| Task update scope | Description only; target group is fixed at creation |
| Group/project name uniqueness | Case-insensitive, unique within scope (groups globally; projects per group) |
| HTML status marks | ✅ ok, ❌ nah, pending cell = white/light background with a `·` dot, no-assignment cell = gray background (no symbol) |
| HTML deprecated projects | Hidden |
| HTML suspended projects | Shown (with visual indicator in column header) |

---

## Architecture

```
viber/
├── pyproject.toml
├── README.md
├── src/
│   └── viber/
│       ├── __init__.py
│       ├── __main__.py       # entry point: from .cli import main; main()
│       ├── errors.py         # all custom exception types
│       ├── models.py         # Pydantic models + enums + assignment_key()
│       ├── store.py          # load_database / save_database
│       ├── path_mapping.py   # map_path + slugify (shared spec compliant)
│       ├── service.py        # all domain logic: CRUD, lifecycle, assignments
│       ├── queries.py        # pending view queries + result types
│       ├── renderer.py       # HTML per-group check page generator
│       ├── formatter.py      # CLI output helpers (shared formatting spec)
│       ├── repl.py           # REPL command parser + interactive flows
│       └── cli.py            # CLI argument parsing + startup
└── tests/
    ├── test_models.py
    ├── test_store.py
    ├── test_service.py
    ├── test_queries.py
    ├── test_path_mapping.py
    ├── test_renderer.py
    └── test_repl.py
```

**Data flow:**

```
CLI args → cli.py → load_database (store.py) → REPL loop (repl.py)
                                                    │
                                          service.py (mutations)
                                          queries.py  (reads)
                                                    │
                                          save_database (store.py)
                                          renderer.py (if --check set)
```

**Layer rules:**
- `repl.py` calls `service.py` and `queries.py`; never accesses `db` directly for logic.
- `service.py` operates on `Database`; never does I/O.
- `formatter.py` is pure output; never calls service or store.
- `renderer.py` is pure output; takes `Database` and writes HTML files.
- Exceptions bubble up to REPL boundary; `repl.py` catches and formats them via `formatter.py`.

---

## Module Specifications

### `errors.py`

```python
class ViberError(Exception): ...
class GroupNotFoundError(ViberError): ...           # "Group {id} not found."
class ProjectNotFoundError(ViberError): ...         # "Project {id} not found."
class TaskNotFoundError(ViberError): ...            # "Task {id} not found."
class AssignmentNotFoundError(ViberError): ...      # "No assignment for p{pid} / t{tid}."
class GroupInUseError(ViberError): ...              # "Group {id} has projects; cannot delete."
class DuplicateNameError(ViberError): ...           # "Name '{name}' already exists."
class InvalidStateTransitionError(ViberError): ...  # if future state rules need enforcement
class PathMappingError(ViberError): ...
class StartupValidationError(ViberError): ...
class FilenameSanitizationError(ViberError): ...    # raised when slugify yields empty string
```

Each exception stores a human-readable message in `args[0]`.

---

### `models.py`

**Enums:**

```python
class ProjectState(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"

class AssignmentStatus(str, Enum):
    PENDING = "pending"
    OK = "ok"
    NAH = "nah"
```

**Pydantic models:**

```python
class Group(BaseModel):
    id: int
    name: str

class Project(BaseModel):
    id: int
    name: str
    group_id: int
    state: ProjectState

class Task(BaseModel):
    id: int
    description: str
    created_utc: str      # ISO 8601 with 'Z' suffix, high precision
    group_id: int | None  # None = applies to all groups

class Assignment(BaseModel):
    project_id: int
    task_id: int
    status: AssignmentStatus
    comment: str | None = None

class Database(BaseModel):
    next_group_id: int = 1
    next_project_id: int = 1
    next_task_id: int = 1
    groups: list[Group] = []
    projects: list[Project] = []
    tasks: list[Task] = []
    # Keyed by composite "project_id-task_id" for O(1) lookup
    assignments: dict[str, Assignment] = {}
```

**Helper function (module-level):**

```python
def assignment_key(project_id: int, task_id: int) -> str:
    return f"{project_id}-{task_id}"
```

---

### `store.py`

```python
def load_database(path: Path) -> Database:
    """Load from JSON file; return empty Database if file does not exist."""

def save_database(db: Database, path: Path) -> None:
    """Serialize to JSON with indent=2, ensure_ascii=False.
    Create parent directories if needed.
    Append trailing newline."""
```

**Serialization notes:**
- Use `db.model_dump(mode="json")` for Pydantic v2.
- Do NOT use `sort_keys=True` globally; preserve field declaration order in dicts.
- Assignment dict keys are strings; Pydantic serializes them correctly.

---

### `path_mapping.py`

**Functions:**

```python
def map_path(
    raw: str,
    *,
    app_root_abs: Path,
    base_dir: Path | None = None,
) -> Path:
    """Map a user-provided path string to an absolute Path.

    Rules (applied in order):
    1. Normalize NFD → NFC.
    2. Reject NUL chars.
    3. Reject Windows rooted-not-qualified forms (\name, C:name).
    4. If starts with ~, expand home dir.
    5. If starts with @, map to app_root_abs.
    6. If absolute, accept as-is.
    7. If relative + base_dir given, join onto base_dir.
    8. If relative + no base_dir, raise PathMappingError.
    9. Resolve dot segments (. and ..) via Path.resolve(strict=False).
    """

def slugify(segment: str) -> str:
    """Apply slugify mode to a single filename segment.

    - Lowercase the input.
    - Split into base and extension at last '.' (if present).
    - In the base: replace any char that is not Unicode letter/digit, _, -, . with -.
    - Collapse runs of - to single -.
    - Strip leading/trailing - and . from base.
    - Reattach extension (also lowercased).
    - Raise FilenameSanitizationError if result is empty after processing.
    """
```

**Private helpers:**
- `_is_windows_rooted_not_fully_qualified(text: str) -> bool`
- `_map_special_prefixes(text: str, app_root_abs: Path) -> Path`

---

### `service.py`

All functions take `db: Database` as first arg, mutate it in-place, and return the affected entity.

**Group operations:**

```python
def create_group(db: Database, name: str) -> Group:
    """Case-insensitive uniqueness check across all groups.
    Allocates db.next_group_id, increments it, appends to db.groups."""

def get_group(db: Database, group_id: int) -> Group:
    """Raises GroupNotFoundError if not found."""

def list_groups(db: Database) -> list[Group]:
    """Returns copy of db.groups (insertion order)."""

def delete_group(db: Database, group_id: int) -> Group:
    """Raises GroupInUseError if any project references this group.
    Removes from db.groups."""
```

**Project operations:**

```python
def create_project(db: Database, name: str, group_id: int) -> Project:
    """Validates group exists. Case-insensitive name uniqueness within group.
    Initial state: ACTIVE. No backfill of existing tasks."""

def get_project(db: Database, project_id: int) -> Project:
    """Raises ProjectNotFoundError."""

def list_projects(db: Database) -> list[Project]:
    """Returns copy of db.projects."""

def set_project_state(db: Database, project_id: int, new_state: ProjectState) -> Project:
    """Allows any state → any state (all transitions are manual and intentional).
    No assignment side effects on transition."""

def delete_project(db: Database, project_id: int) -> Project:
    """Cascade-deletes all assignments where project_id matches.
    Removes from db.projects."""
```

**Task operations:**

```python
def create_task(
    db: Database,
    description: str,
    group_id: int | None,
) -> Task:
    """Validates group exists if group_id is not None.
    Sets created_utc = datetime.now(timezone.utc).isoformat() with 'Z' marker.
    Generates PENDING assignments ONLY for projects with state=ACTIVE that match
    the task's group_id (or all ACTIVE projects if group_id is None)."""

def get_task(db: Database, task_id: int) -> Task:
    """Raises TaskNotFoundError."""

def list_tasks(db: Database) -> list[Task]:
    """Returns copy of db.tasks."""

def update_task_description(db: Database, task_id: int, description: str) -> Task:
    """Updates description only; group_id is immutable."""

def delete_task(db: Database, task_id: int) -> Task:
    """Cascade-deletes all assignments where task_id matches.
    Removes from db.tasks."""
```

**Assignment operations:**

```python
def get_assignment(db: Database, project_id: int, task_id: int) -> Assignment:
    """Raises AssignmentNotFoundError if key not in db.assignments."""

def resolve_assignment(
    db: Database,
    project_id: int,
    task_id: int,
    status: AssignmentStatus,
    comment: str | None,
) -> Assignment:
    """Validates project and task exist. Gets assignment (raises if missing).
    Updates status and comment in-place."""
```

**Private helpers:**

```python
def _check_group_name_unique(db: Database, name: str, exclude_id: int | None) -> None:
    """Case-insensitive comparison. Raises DuplicateNameError."""

def _check_project_name_unique(
    db: Database, name: str, group_id: int, exclude_id: int | None
) -> None:
    """Case-insensitive comparison within the same group. Raises DuplicateNameError."""
```

---

### `queries.py`

**Result types:**

```python
@dataclass
class PendingTask:
    task: Task
    assignment: Assignment

@dataclass
class PendingProject:
    project: Project
    group: Group
    assignment: Assignment
```

**Query functions:**

```python
def pending_all(db: Database) -> list[tuple[Project, Group, Task, Assignment]]:
    """Return all pending assignments, excluding SUSPENDED and DEPRECATED projects.
    Ordered by: group name asc, project name asc, task created_utc asc."""

def pending_by_project(db: Database, project_id: int) -> list[tuple[Task, Assignment]]:
    """Pending tasks for one project.
    Raises ProjectNotFoundError if project not found.
    Returns empty list if project is suspended/deprecated (view excludes them)."""

def pending_by_task(db: Database, task_id: int) -> list[tuple[Project, Group, Assignment]]:
    """Pending projects for one task, excluding suspended/deprecated.
    Raises TaskNotFoundError if task not found."""
```

---

### `renderer.py`

```python
def render_check_pages(db: Database, check_base: Path) -> None:
    """Generate one HTML file per group.

    Output path: {check_base.stem}-{slugify(group.name)}{check_base.suffix}
    written to check_base.parent.

    Per-group table:
    - Rows = tasks sorted by created_utc descending (newest first).
    - Columns = projects in group, sorted by name ascending.
    - Exclude DEPRECATED projects from columns.
    - Show SUSPENDED projects with "(suspended)" in column header.
    - Cell content:
        - Has assignment + status PENDING → white cell, · dot
        - Has assignment + status OK     → white cell, ✅
        - Has assignment + status NAH    → white cell, ❌
        - No assignment (lifecycle gap)  → gray cell, no symbol
    - Task rows include: task description, created date (local time display).
    """
```

HTML template: minimal inline CSS, no external dependencies. Self-contained.

---

### `formatter.py`

```python
def print_blank() -> None:
    """Print one blank line."""

def print_segment(lines: Iterable[str]) -> None:
    """Print a blank line, then each line in lines."""

def format_group(group: Group) -> str:
    """Return 'g{id}: {name}'"""

def format_project(project: Project, group: Group) -> str:
    """Return 'p{id}: {name} [{state}] (group: {group.name})'"""

def format_task(task: Task, db: Database) -> str:
    """Return 't{id}: {description} [created: {local_time}]'
    Include target group name if task.group_id is set, else 'all groups'."""

def format_assignment(assignment: Assignment, project: Project, task: Task) -> str:
    """Return 'p{pid} / t{tid}: {status}' + optional comment."""

def format_local_time(utc_iso: str) -> str:
    """Parse UTC ISO string, convert to local time, format as 'YYYY-MM-DD HH:MM:SS'."""
```

---

### `repl.py`

**Command grammar:**

```
create group <name>
create project <name> g<ID>
create task <description> [g<ID>]

read groups
read projects
read tasks
read g<ID>
read p<ID>
read t<ID>

update p<ID> active|suspended|deprecated
update t<ID>          ← interactive: shows current, prompts new description

delete g<ID>
delete p<ID>
delete t<ID>

view                  ← all pending (active projects only)
view p<ID>            ← pending tasks for one project
view t<ID>            ← pending projects for one task

ok p<ID> t<ID>        ← also accepts: ok t<ID> p<ID>
ok t<ID> p<ID>
nah p<ID> t<ID>
nah t<ID> p<ID>

work p<ID>            ← iterate pending tasks for project
work t<ID>            ← iterate pending projects for task

help
exit
quit
```

**Aliases:** `c`=create, `r`=read, `u`=update, `d`=delete, `v`=view, `o`=ok, `n`=nah, `w`=work
`exit` and `quit` have no single-letter aliases.

**`ok`/`nah` interactive flow:**
1. Resolve entity references (validate p and t exist, assignment exists and is pending).
2. Print a summary of what will be resolved (project name, task description, current status).
3. Confirm: `Confirm? [y/N]:` — abort if not `y`/`yes`.
4. Prompt: `Comment (optional, Enter to skip):` — capture optional freetext.
5. Call `resolve_assignment`.

**`work` loop flow (work p<ID>):**
1. Fetch all pending tasks for the project.
2. If none: print "No pending tasks for p{id}." and return.
3. For each pending task, one at a time:
   - Print task details.
   - Prompt: `[o]k / [n]ah / [s]kip / [q]uit:`.
   - `o` → run ok flow (comment prompt), then move to next.
   - `n` → run nah flow (comment prompt), then move to next.
   - `s` → move to next without change.
   - `q` → exit work loop.

**Prompt prefix:** `> ` (before each command input).

**Error handling in REPL:**
- Catch `ViberError` subtypes → print error message as a plain segment.
- Catch `KeyboardInterrupt` → print empty line, continue loop (do not exit).
- `exit`/`quit` → break loop cleanly.

---

### `cli.py`

```python
@dataclass
class AppArgs:
    data_path: Path
    check_path: Path | None   # None when --check not provided

def parse_args() -> AppArgs | None:
    """Parse sys.argv.
    --help: print help and return None (caller exits).
    --data PATH: required.
    --check PATH: optional.
    Default for --data if not provided: error (must be explicit).
    """

def main() -> None:
    """Entry point.
    1. parse_args() → if None, exit 0.
    2. Resolve --data and --check paths via map_path (app_root = package dir).
    3. load_database(data_path).
    4. If --check provided and db has content, render initial HTML.
    5. Run REPL loop.
    6. On REPL exit, save_database.
    """
```

**Path resolution:**
- `app_root_abs` = `Path(__file__).parent` (the package directory).
- `--data` and `--check` paths are resolved via `map_path`.
- Pure relative paths for `--data`/`--check` → raise `StartupValidationError`
  (no base_dir, per spec: pure relative requires explicit base).
  Users must use `~`, `@`, or absolute paths.

**Mutation hook:**
Every REPL command that mutates state must call:
1. `save_database(db, data_path)`
2. `render_check_pages(db, check_path)` if `check_path is not None`

---

## Implementation Steps

### Phase 1: Foundation

- [ ] Create `pyproject.toml` with project metadata, `[project.scripts]` entry for `viber`, dev deps `pydantic pytest ruff mypy`.
- [ ] Create `src/viber/__init__.py` (empty).
- [ ] Create `src/viber/__main__.py` → `from .cli import main; main()`.
- [ ] Implement `errors.py` with all exception classes.
- [ ] Implement `models.py`: enums, Pydantic models, `assignment_key()`.
- [ ] Implement `store.py`: `load_database`, `save_database`.
- [ ] Write `tests/test_store.py`: round-trip, missing file returns empty DB.

### Phase 2: Path Utilities

- [ ] Implement `path_mapping.py`: `map_path`, `slugify`, private helpers.
- [ ] Write `tests/test_path_mapping.py`: NUL rejection, ~, @, absolute, relative+base, relative+no-base, Windows rooted-not-qualified, dot segments, slugify cases.

### Phase 3: Domain Services

- [ ] Implement `service.py` group functions.
- [ ] Implement `service.py` project functions.
- [ ] Implement `service.py` task functions (including assignment generation).
- [ ] Implement `service.py` assignment functions.
- [ ] Write `tests/test_service.py`:
  - [ ] Group CRUD + delete blocked when projects exist.
  - [ ] Project CRUD + cascade delete.
  - [ ] Task creation generates pending assignments for active+matching projects only.
  - [ ] Task creation skips suspended/deprecated projects.
  - [ ] Task creation skips projects in wrong group.
  - [ ] Assignment not backfilled for projects created after task.
  - [ ] Task cascade delete removes assignments.
  - [ ] Project cascade delete removes assignments.
  - [ ] set_project_state allows any transition.
  - [ ] Case-insensitive uniqueness enforced for groups.
  - [ ] Case-insensitive uniqueness enforced for projects within group.
  - [ ] Duplicate name raises DuplicateNameError.

### Phase 4: Queries

- [ ] Implement `queries.py`: `pending_all`, `pending_by_project`, `pending_by_task`.
- [ ] Write `tests/test_queries.py`:
  - [ ] pending_all excludes SUSPENDED and DEPRECATED.
  - [ ] pending_all includes ACTIVE only.
  - [ ] pending_by_project returns empty if project is not ACTIVE.
  - [ ] pending_by_task excludes SUSPENDED/DEPRECATED.
  - [ ] Ordering is correct.

### Phase 5: Output

- [ ] Implement `formatter.py`: all format/print helpers.
- [ ] Implement `renderer.py`: `render_check_pages`, HTML template.
- [ ] Write `tests/test_renderer.py`:
  - [ ] Deprecated projects excluded from HTML columns.
  - [ ] Suspended projects included with "(suspended)" label.
  - [ ] Gray cells for no-assignment lifecycle gaps.
  - [ ] Tasks ordered newest-first.
  - [ ] Correct symbols for each status.
  - [ ] File is named with slugified group name.

### Phase 6: REPL and CLI

- [ ] Implement `cli.py`: `AppArgs`, `parse_args`, `main`.
- [ ] Implement `repl.py`: REPL loop, command parser, all commands, ok/nah flow, work loop.
- [ ] Write `tests/test_repl.py`:
  - [ ] ok accepts both token orders.
  - [ ] nah accepts both token orders.
  - [ ] work loop processes pending, skip works, quit exits.
  - [ ] view with no pending shows correct message.
  - [ ] Unknown command shows helpful error.
  - [ ] exit/quit recognized; c/r/u/d/v/o/n/w recognized.

### Phase 7: Quality Gate

- [ ] Run `ruff check src/ tests/` and fix all issues.
- [ ] Run `mypy src/` (strict mode if feasible) and fix type errors.
- [ ] Run `pytest tests/` and confirm all pass.
- [ ] Write `README.md` with full-word command examples first, alias forms second.

---

## Data File Format (JSON schema)

```json
{
  "next_group_id": 3,
  "next_project_id": 5,
  "next_task_id": 4,
  "groups": [
    { "id": 1, "name": "Backend" },
    { "id": 2, "name": "Frontend" }
  ],
  "projects": [
    { "id": 1, "name": "api-server", "group_id": 1, "state": "active" },
    { "id": 2, "name": "auth-service", "group_id": 1, "state": "suspended" }
  ],
  "tasks": [
    { "id": 1, "description": "Update dependencies", "created_utc": "2026-02-26T10:00:00.000000Z", "group_id": null },
    { "id": 2, "description": "Fix lint warnings", "created_utc": "2026-02-26T11:00:00.000000Z", "group_id": 1 }
  ],
  "assignments": {
    "1-1": { "project_id": 1, "task_id": 1, "status": "pending", "comment": null },
    "1-2": { "project_id": 1, "task_id": 2, "status": "ok", "comment": "Done in PR #42" }
  }
}
```

---

## HTML Check Page Format

File naming: `{stem}-{slugify(group_name)}{suffix}` in same directory as `--check` path.

Example `check.html` → `check-backend.html`.

Structure:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Viber Check — {group_name}</title>
  <style>
    /* minimal table styles, no external deps */
    table { border-collapse: collapse; }
    th, td { border: 1px solid #ccc; padding: 4px 8px; text-align: center; }
    .task-desc { text-align: left; }
    .gap { background: #ccc; }   /* lifecycle gap: gray */
  </style>
</head>
<body>
  <h1>{group_name}</h1>
  <p>Generated: {local datetime}</p>
  <table>
    <thead>
      <tr>
        <th>Task</th>
        <th>Created</th>
        <!-- one <th> per non-deprecated project, sorted by name -->
        <th>p1-name</th>
        <th>p2-name (suspended)</th>
      </tr>
    </thead>
    <tbody>
      <!-- one <tr> per task, newest first -->
      <tr>
        <td class="task-desc">Update dependencies</td>
        <td>2026-02-26</td>
        <td>·</td>            <!-- pending -->
        <td class="gap"></td> <!-- lifecycle gap -->
      </tr>
      <tr>
        <td class="task-desc">Fix lint warnings</td>
        <td>2026-02-26</td>
        <td>✅</td>
        <td class="gap"></td>
      </tr>
    </tbody>
  </table>
</body>
</html>
```

---

## Open Questions (Post-Session)

- Confirm whether `ruff` strict mode and `mypy --strict` are desired, or default modes only.
- Confirm whether `viber` should be installable as a global CLI tool (editable install via `uv tool`) or run via `uv run viber`.
- Confirm whether the no-pending message "Vibe is good. No pending assignments." is the desired wording.
