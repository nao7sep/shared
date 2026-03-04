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
cd /path/to/shared/apps/tk
uv sync
```

### 2. Create a profile
```bash
uv run tk init -p ~/work/my-profile.json
```

This creates a profile with:
- Your system timezone
- Subjective day starting at 04:00:00
- `tasks.json` for data storage
- `TODO.md` for current task list

### 3. Start the REPL
```bash
uv run tk -p ~/work/my-profile.json
```

You'll see:
```
tk 0.1.0

Profile Information:
  Timezone:                  America/New_York
  DST:                       No
  Current time:              2026-02-08 22:48:10
  Subjective day starts at:  04:00:00

Type 'exit' or 'quit' to exit, or Ctrl-D

>
```

Type `help` to see available commands.

### 4. Use it
```
> a implement user login
Task added.

> l
1. implement user login

> d 1
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
After running `list`, `history`, `today`, `yesterday`, or `recent`, you reference tasks by their displayed number:
```
> l
1. task one
2. task two

> d 1    # completes "task one"
```

Numbers are only valid until you run another command that changes the list.

### Interactive Prompts

When marking tasks as done or canceled, tk prompts for an optional note and an optional date override.

**Prompt behavior:**
- Press Enter to skip optional fields
- Press Ctrl+C to cancel entire operation
- Use `note` and `date` commands later if you want to update handled tasks

**Delete confirmation:**
```
> delete 1
Task: old task
Status: pending
Delete permanently? (yes/N): yes
Task deleted.
```

### Profile Structure

**Path shortcuts** in data_path/output_path:
- `~/dir/file` → your home directory
- `@/dir/file` → source package directory
- `~\dir\file` and `@\dir\file` are also accepted (normalized to path separators)
- `./dir/file` or `file` → relative to profile directory
- `/abs/path` → absolute path used as-is

**Note**: Profile file paths passed via `--profile` must be absolute or use `~/` or `@/` (relative profile paths are rejected).

A profile JSON contains:

```json
{
  "data_path": "./tasks.json",
  "output_path": "./TODO.md",
  "timezone": "America/New_York",
  "subjective_day_start": "04:00:00",
  "auto_sync": true,
  "sync_on_exit": false
}
```

- `timezone`: Required. IANA timezone (for example `"Asia/Tokyo"`).
- `subjective_day_start`: Required. Day boundary in `HH:MM` or `HH:MM:SS`.
- `data_path`: Required. Where `tasks.json` is stored.
- `output_path`: Required. Where `TODO.md` is generated.
- `auto_sync`: Optional. Regenerate `TODO.md` after changes. Default: `true`.
- `sync_on_exit`: Optional. Regenerate `TODO.md` on exit. Default: `false`.

## Commands

All commands support shortcuts shown in parentheses.

### Adding & Viewing

**add (a)** `<text>` - Add a task
```
> a implement authentication
> add fix navigation bug
```

**list (l)** - Show pending tasks
```
> l
```

**help** - Show available commands
```
> help
```

**history (h)** `[--days N] [--working-days N]` - Show completed/canceled tasks
```
> h                     # all history
> h --days 7            # last 7 calendar days
> h --working-days 5    # last 5 days with tasks
```

**today (t)** - Show today's handled tasks
**yesterday (y)** - Show yesterday's handled tasks
**recent (r)** - Show last 3 working days

### Completing Tasks

**done (d)** `<num>` - Mark as done (with interactive prompts)
```
> d 1
```

**cancel (c)** `<num>` - Mark as canceled (with interactive prompts)
```
> c 2
```

### Editing

**edit (e)** `<num> <text>` - Change task text
```
> e 1 new task description
```

**note (n)** `<num> [<text>]` - Add/update/remove note (handled tasks only)
```
> n 1 additional context
> n 1                    # removes note
```

**date** `<num> <YYYY-MM-DD>` - Change subjective date (handled tasks only)
```
> date 1 2026-02-05
```

**delete** `<num>` - Permanently delete task (requires confirmation)
```
> delete 1
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
- ❌ canceled task

### 2026-02-05
- ✅ another done task
```

## Tips

- **Use shortcuts:** `a`, `l`, `d`, `c`, `e` for speed
- **Update after handling:** Use `note <num> [<text>]` and `date <num> <YYYY-MM-DD>` on handled tasks
- **Unknown handled date:** If a handled task has no subjective date (from manual JSON edits), it appears under `unknown` in both `history` output and `TODO.md`
- **No duplicate checking:** Intentional design choice - just cancel or delete if needed
- **Delete is rare:** Use `cancel` for tasks you won't do; reserve `delete` for mistakes

## Troubleshooting

**"Run 'list' or 'history' first" error:** You tried a number-based command without a current list. Run `list`, `history`, `today`, `yesterday`, or `recent` first.

**"Unknown command" error:** Check for typos or unsupported commands. Use `help` in REPL to see valid commands.

**Numbers not working:** Task numbers reset after state-changing commands (add, edit, done, etc). Run `list` or another view command again.

## Advanced Usage

### Manual Data Edits
You can edit tasks.json directly, but:
- Always keep valid JSON structure
- Tasks without `subjective_date` will appear as "unknown" in history
- Running any command will validate and may fail if structure is invalid

## Windows & One-File Packaging Notes

These are current project assumptions, documented for future packaging work:

- Windows `.exe` one-file packaging is not an active goal right now.
- Timezone behavior on Windows is expected to depend on runtime packaging details (for example bundled timezone data); verify during actual packaging/testing.
- `@/` paths resolve to the source package directory.
