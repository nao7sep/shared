# tk

A timezone-aware CLI task manager with subjective day tracking.

## What is tk?

**tk** helps you track tasks across different timezones with a "subjective day" concept. If your day starts at 4 AM instead of midnight, tk handles that. It maintains a TODO.md file and stores task history with proper date attribution.

**Key features:**
- Timezone-aware with configurable day start time (default: 4 AM)
- Simple REPL interface with single-letter shortcuts
- Automatic TODO.md generation
- Task history tracking with subjective dates
- Interactive confirmation for task completion

## Quick Start

### 1. Install
```bash
poetry install
```

### 2. Create a profile
```bash
poetry run tk init -p ~/work/my-profile.json
```

This creates a profile with:
- Your system timezone
- Subjective day starting at 04:00:00
- `tasks.json` for data storage
- `TODO.md` for current task list

### 3. Start the REPL
```bash
poetry run tk -p ~/work/my-profile.json
```

### 4. Use it
```
tk> a implement user login
Task added.

tk> l
1. implement user login

tk> d 1
Task: implement user login
Will be marked as: done
Subjective date: 2026-02-06
(Press Ctrl+C to cancel)
Note (press Enter to skip): finished
Date override (press Enter to use 2026-02-06): 
Task marked as done.
```

## Core Concepts

### Subjective Date
If it's 2 AM and you haven't slept yet, it still feels like yesterday. tk uses a "subjective day start" time (default: 4 AM) to attribute tasks to the day that feels right.

Example: Mark a task done at 3 AM on Feb 6th → recorded as completed on Feb 5th.

### Number-Based Workflow
After running `list` or `history`, you reference tasks by their displayed number:
```
tk> l
1. task one
2. task two

tk> d 1    # completes "task one"
```

Numbers are only valid until you run another command that changes the list.

### Profile Structure
A profile JSON contains:
- `timezone`: IANA timezone (e.g., "Asia/Tokyo")
- `subjective_day_start`: Time when your day starts (e.g., "04:00:00")
- `data_path`: Where tasks.json is stored (relative paths supported)
- `output_path`: Where TODO.md is generated
- `auto_sync`: Auto-regenerate TODO.md after changes (default: true)
- `sync_on_exit`: Regenerate TODO.md on exit (default: false)

## Commands

All commands support shortcuts shown in parentheses.

### Adding & Viewing

**add (a)** `<text>` - Add a task
```
tk> a implement authentication
tk> add fix navigation bug
```

**list (l)** - Show pending tasks
```
tk> l
```

**history (h)** `[--days N] [--working-days N]` - Show completed/cancelled tasks
```
tk> h                      # all history
tk> h --days 7            # last 7 calendar days
tk> h --working-days 5    # last 5 days with tasks
```

**today (t)** - Show today's completed tasks
**yesterday (y)** - Show yesterday's completed tasks
**recent (r)** - Show last 3 working days

### Completing Tasks

**done (d)** `<num>` - Mark as done (with interactive prompts)
```
tk> d 1
tk> d 1 --note "deployed to prod" --date 2026-02-05
```

**cancel (c)** `<num>` - Mark as cancelled
```
tk> c 2
tk> c 2 --note "no longer needed"
```

### Editing

**edit (e)** `<num> <text>` - Change task text
```
tk> e 1 new task description
```

**note (n)** `<num> [<text>]` - Add/update/remove note
```
tk> n 1 additional context
tk> n 1                    # removes note
```

**date** `<num> <YYYY-MM-DD>` - Change subjective date (handled tasks only)
```
tk> date 1 2026-02-05
```

**delete** `<num>` - Permanently delete task (requires confirmation)
```
tk> delete 1
```

### Other

**sync (s)** - Regenerate TODO.md manually
**exit** / **quit** - Exit REPL

## TODO.md Format

Generated automatically after each change (if `auto_sync: true`):

```markdown
# TODO

- pending task one
- pending task two

## History

### 2026-02-06
- ✅ completed task => note here
- ❌ cancelled task

### 2026-02-05
- ✅ another done task
```

## Tips

- **Numbers reset:** After any command that changes state, run `list` or `history` again to get fresh numbers
- **Use shortcuts:** `a`, `l`, `d`, `c`, `e` for speed
- **Ctrl+C cancels:** Interactive prompts can be cancelled anytime
- **Unknown handled date:** If a handled task has no subjective date (for example from manual JSON edits), it appears under `unknown` in both `history` output and `TODO.md`
- **No duplicate checking:** Intentional design choice - just cancel or delete if needed
- **Delete is rare:** Use `cancel` for tasks you won't do; reserve `delete` for mistakes

## Installation for Daily Use

After `poetry install`, you can either:

**Option 1:** Use poetry shell
```bash
cd /path/to/tk
poetry shell
tk -p ~/my-profile.json
```

**Option 2:** Create an alias
```bash
alias tk='poetry run --directory /path/to/tk tk'
tk -p ~/my-profile.json
```

**Option 3:** Install in editable mode
```bash
cd /path/to/tk
pip install -e .
tk -p ~/my-profile.json
```

## Windows & One-File Packaging Notes

These are current project assumptions, documented for future packaging work:

- Windows `.exe` one-file packaging is not an active goal right now.
- Timezone behavior on Windows is expected to depend on runtime packaging details (for example bundled timezone data); verify during actual packaging/testing.
- `@/` paths are intended for source/project usage. In one-file packaged mode they may be unreliable, so avoid them there.
- Backslash-style path shortcuts for `~`/`@` are not a supported input style in this project.
