# tk

A quick CLI app to manage tasks.

## Installation

```bash
poetry install
```

## Usage

```bash
# Run with poetry
poetry run tk --profile ~/path/to/profile.json

# Or activate virtualenv first, then run
poetry shell
tk --profile ~/path/to/profile.json
```

## Quick Start

1. Create a new profile:
```bash
poetry run tk new --profile ~/work/my-profile.json
# or use short form
poetry run tk new -p ~/work/my-profile.json
```

2. Start the app with your profile:
```bash
poetry run tk --profile ~/work/my-profile.json
# or use short form
poetry run tk -p ~/work/my-profile.json
```

3. Use the app (see Commands below)

## Commands

All commands support short forms (shown in parentheses).

### Task Management

- **add (a)** `<text>` - Add a new task
  ```
  tk> add "implement user authentication"
  tk> a "fix bug in login"
  ```

- **list (l)** - List all pending tasks
  ```
  tk> list
  tk> l
  ```

- **history (h)** `[--days N] [--working-days N]` - List handled (done/cancelled) tasks
  ```
  tk> history
  tk> h --days 7
  tk> h --working-days 5
  ```
  Note: `--days` shows last N calendar days, `--working-days` shows last N days with tasks. Cannot use both.

- **today (t)** - List tasks handled today
  ```
  tk> today
  tk> t
  ```

- **yesterday (y)** - List tasks handled yesterday
  ```
  tk> yesterday
  tk> y
  ```

- **recent (r)** - List tasks from last 3 working days (including today)
  ```
  tk> recent
  tk> r
  ```

### Handling Tasks

- **done (d)** `<num>` - Mark task as done (interactive)
  ```
  tk> list
  tk> done 1
  tk> d 2 --note "completed" --date 2026-01-30
  ```

- **cancel (c)** `<num>` - Mark task as cancelled (interactive)
  ```
  tk> cancel 1
  tk> c 2 --note "not needed"
  ```

### Editing Tasks

- **edit (e)** `<num> <text>` - Change task text
  ```
  tk> list
  tk> edit 1 new task text
  tk> e 2 updated text
  ```

- **note (n)** `<num> [<text>]` - Set/update/remove task note
  ```
  tk> list
  tk> note 1 "added details"
  tk> n 2        # removes note
  ```

- **date** `<num> <YYYY-MM-DD>` - Change subjective handling date (no short form)
  ```
  tk> history
  tk> date 1 2026-01-30
  ```
  Note: Only works on handled (done/cancelled) tasks. Cannot set date on pending tasks.

- **delete** `<num>` - Delete task permanently (no short form)
  ```
  tk> delete 1
  ```
  Note: Delete has no shortcut since it's dangerous and rarely needed. Use `cancel` instead if you just don't want to do the task.

### Other Commands

- **sync (s)** - Regenerate TODO.md from data
  ```
  tk> sync
  ```

- **exit** / **quit** - Exit the app
  ```
  tk> exit
  ```

## Interactive Confirmation

When using `done` or `cancel` without `--note` and `--date` flags, the app will:
1. Show the task and calculated subjective date
2. Prompt for a note (Enter to skip)
3. Prompt for date override (Enter to use calculated date)
4. Ask for confirmation before proceeding

This helps prevent mistakes when handling tasks.

## Design Decisions

**No duplicate checking:** The app does not check if a task already exists when adding or editing. Simple string comparison wouldn't catch meaningful duplicates, and AI-based semantic checking would add complexity without much benefit. If you accidentally add a duplicate, just cancel or delete it.

**Sync settings:** Profiles include `auto_sync` (default: true) and `sync_on_exit` (default: false). With `auto_sync` enabled, TODO.md regenerates after every data change. The `sync` command always works regardless of settings.

See _WHAT.md and _HOW.md for detailed documentation.
