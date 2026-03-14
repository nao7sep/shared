# viber

Local REPL tool for tracking repeated cross-project maintenance tasks.

**Purpose:** Maintain vibe-coding speed and quality with minimal overhead for repetitive maintenance checks.

## Setup

```sh
cd apps/viber
uv sync
```

## Usage

```sh
uv run viber --data ~/viber/data.json
uv run viber --data ~/viber/data.json --check ~/viber/check.html
uv run viber --help  # or -h
```

`--data` is required. If the file does not exist yet, viber starts with an empty database and creates it on the first save. `--check` enables per-group HTML output.

## REPL Commands

Full-word commands (aliases in parentheses):

```
create group <name>                    (c g <name>)
create project <name> g<ID>            (c p <name> g<ID>)
create task <description> <all|g<ID>>  (c t <description> <all|g<ID>>)

read groups                            (r groups)
read projects                          (r projects)
read tasks                             (r tasks)
read g<ID>                             (r g<ID>)
read p<ID>                             (r p<ID>)
read t<ID>                             (r t<ID>)

update g<ID> <new-name>                (u g<ID> <new-name>)
update p<ID> name <new-name>           (u p<ID> name <new-name>)
update p<ID> state <state>             (u p<ID> state <state>)
update t<ID> <new-description>         (u t<ID> <new-description>)
update t<ID>                           (u t<ID>)
update p<ID> t<ID> [comment]           (u p<ID> t<ID> [comment])

delete g<ID>                           (d g<ID>)
delete p<ID>                           (d p<ID>)
delete t<ID>                           (d t<ID>)

view                                   (v)
view p<ID>                             (v p<ID>)
view t<ID>                             (v t<ID>)

ok p<ID> t<ID>                         (o p<ID> t<ID>)
nah p<ID> t<ID>                        (n p<ID> t<ID>)

undo p<ID> t<ID>                       (z p<ID> t<ID>)
undo g<ID>                             (z g<ID>)
undo p<ID>                             (z p<ID>)
undo t<ID>                             (z t<ID>)

work p<ID>                             (w p<ID>)
work t<ID>                             (w t<ID>)

help
exit | quit
```

### Notes

- Commands that operate on a project/task pair accept `p<ID>` and `t<ID>` in either order: `update ... [comment]`, `ok`, `nah`, and `undo`. Example: `ok p3 t1` or `ok t1 p3`. No confirmation is required for `ok`/`nah`; they only prompt for an optional comment, and `Ctrl+C` during that prompt cancels.
- `undo p<ID> t<ID>` reverts a single assignment to `pending` (no confirmation). `undo g<ID>`, `undo p<ID>`, and `undo t<ID>` revert all resolved assignments for that entity (requires y/N confirmation). Comments are always cleared on undo.
- `create task` requires explicit scope: trailing `g<ID>` for one group or `all` for all groups.
- Use explicit project update forms only: `update p<ID> name ...` and `update p<ID> state ...`.
- Bare `update t<ID>` shows the current description and prompts for a new one. `Ctrl+C`, `Ctrl+D`, or empty input cancels.
- `update p<ID> t<ID>` with no comment clears the assignment comment.
- Deletes are cascading: deleting a group also deletes its projects and group-scoped tasks; deleting a project/task deletes related assignments.
- Tasks persist even when they currently have no assignments, so future or revived projects can inherit them.
- All `delete` commands require `y` or `yes`; Enter or any other input cancels.
- `view` shows `project | group | task`; `view p<ID>` and `view t<ID>` show header row + matching rows (no timestamps).
- `work` shows all pending items, then prompts for item number (or `q` to quit), then action `[o]k / [n]ah / [c]ancel`, then optional comment (Enter to skip).
- In `work`, pressing `Ctrl+C` at any prompt cancels the current step safely.
- `exit` and `quit` are full-word only (no single-letter aliases).
- CLI output follows the shared segment-spacing rule: the first segment has no leading blank line, later segments own one leading blank line, and no segment emits a trailing blank line. Startup warnings can therefore appear before the banner, and the banner will then start with its own leading blank line.

## Concepts

| Entity | Description |
|---|---|
| Group | A named category (e.g. "Backend", "Frontend"). |
| Project | A repo or service, belongs to exactly one group, with `created_utc`. |
| Task | A maintenance check, scoped to one group or all groups, with `created_utc`. |
| Assignment | Per-project state for a task: `pending`, `ok`, or `nah`, with optional `handled_utc`. |

### Project states

- `active` — receives new task assignments when tasks are created, and is caught up to any older applicable tasks when the project is created or revived.
- `suspended` — paused; excluded from `view` but shown in HTML check pages.
- `deprecated` — retired; excluded from `view` and HTML check pages.

New tasks generate assignments only for projects that are `active` at task creation time. Tasks created while a project is `suspended` or `deprecated` remain missing assignments until that project is set back to `active`, at which point viber backfills all applicable missing assignments.

### Timestamps

- All timestamps are stored as UTC ISO 8601 with `Z` suffix.
- `project.created_utc` is set when a project is created.
- `task.created_utc` is set when a task is created.
- `assignment.handled_utc` is `null` while pending, set when resolved via `ok` or `nah`, and cleared by `undo`.
- `read projects` / `read p<ID>` display `project | group | state | local-created-time`.
- `read tasks` / `read t<ID>` display `task | group-or-all | local-created-time`.

## HTML Check Pages

When `--check ~/viber/check.html` is given, viber writes one file per group on startup when groups already exist, and again after each mutation:

- `check-backend.html`, `check-frontend.html`, …
- Each page shows the group's tasks against its non-deprecated projects.
- ✅ ok · ❌ nah · blank cell pending · gray cell = task created while that project was inactive; the missing assignment will be created when the project is revived.

## Path Syntax

Both `--data` and `--check` accept:

- Absolute paths: `/home/user/viber/data.json`
- Home-relative: `~/viber/data.json`
- App-root-relative: `@/data.json`

Here, "app root" means the viber package directory used by the app itself. In this repo,
`@/...` resolves under `src/viber/`, matching the same convention used by `autopage`.

Pure relative paths (no prefix) are rejected.
