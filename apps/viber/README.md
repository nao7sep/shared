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
```

`--data` is required. `--check` enables per-group HTML output (regenerated after each mutation).

## REPL Commands

Full-word commands (aliases in parentheses):

```
create group <name>                         (c g <name>)
create project <name> g<ID>                 (c p <name> g<ID>)
create task <description> [g<ID>]           (c t <description> [g<ID>])

read groups                                 (r groups)
read projects                               (r projects)
read tasks                                  (r tasks)
read g<ID>                                  (r g<ID>)
read p<ID>                                  (r p<ID>)
read t<ID>                                  (r t<ID>)

update p<ID> active|suspended|deprecated    (u p<ID> <state>)
update g<ID> <new-name>                     (u g<ID> <new-name>)
update p<ID> name <new-name>                (u p<ID> name <new-name>)
update p<ID> state <state>                  (u p<ID> state <state>)
update t<ID> <new-description>              (u t<ID> <new-description>)
update p<ID> t<ID> [comment]                (u p<ID> t<ID> [comment])
update t<ID> p<ID> [comment]                (u t<ID> p<ID> [comment])

delete g<ID>                                (d g<ID>)
delete p<ID>                                (d p<ID>)
delete t<ID>                                (d t<ID>)

view                                        (v)
view p<ID>                                  (v p<ID>)
view t<ID>                                  (v t<ID>)

ok p<ID> t<ID>                              (o p<ID> t<ID>)
nah p<ID> t<ID>                             (n p<ID> t<ID>)

work p<ID>                                  (w p<ID>)
work t<ID>                                  (w t<ID>)

help
exit | quit
```

### Notes

- `ok` and `nah` accept tokens in either order: `ok p3 t1` or `ok t1 p3`.
- `create task <description> g<ID>` — the trailing `g<ID>` scopes the task to one group; omit for all groups.
- `update p<ID>` transitions project lifecycle state (`active` → `suspended` → `deprecated`, any direction).
- `update p<ID> <name>` is supported as a shorthand rename form.
- `update p<ID> t<ID>` with no comment clears the assignment comment.
- `work` loops through pending items one by one with `[o]k / [n]ah / [s]kip / [q]uit` prompts.
- `exit` and `quit` are full-word only (no single-letter aliases).

## Concepts

| Entity | Description |
|---|---|
| Group | A named category (e.g. "Backend", "Frontend"). |
| Project | A repo or service, belongs to exactly one group. |
| Task | A maintenance check, scoped to one group or all groups. |
| Assignment | Per-project state for a task: `pending`, `ok`, or `nah`. |

### Project states

- `active` — receives new task assignments when tasks are created.
- `suspended` — paused; excluded from `view` but shown in HTML check pages.
- `deprecated` — retired; excluded from `view` and HTML check pages.

Assignments are only generated for `active` projects at task creation time. No backfilling.

## HTML Check Pages

When `--check ~/viber/check.html` is given, viber writes one file per group after each mutation:

- `check-backend.html`, `check-frontend.html`, …
- Rows = tasks (newest first), columns = non-deprecated projects.
- ✅ ok · ❌ nah · blank cell pending · gray cell = lifecycle gap (no assignment).

## Path Syntax

Both `--data` and `--check` accept:

- Absolute paths: `/home/user/viber/data.json`
- Home-relative: `~/viber/data.json`
- App-root-relative: `@/data.json`

Pure relative paths (no prefix) are rejected.
