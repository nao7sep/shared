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
Profile Information:
  Timezone: America/New_York
  DST: No
  Current time: 2026-02-08 22:48:10
  Subjective day starts at: 04:00:00

tk task manager
Type 'exit' or 'quit' to exit, or Ctrl-D

tk> 
```

Type `help` to see available commands.

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

### Interactive Prompts

When marking tasks as done or cancelled, tk prompts for details:

```
tk> d 1
Task: implement user login
Will be marked as: done
Subjective date: 2026-02-06
(Press Ctrl+C to cancel)
Note (press Enter to skip): deployed to staging
Date override (press Enter to use 2026-02-06): 2026-02-05
Task marked as done.
```

**Prompt behavior:**
- Press Enter to skip optional fields
- Press Ctrl+C to cancel entire operation
- Use `note` and `date` commands later if you want to update handled tasks

**Delete confirmation:**
```
tk> delete 1
Task: old task
Status: pending

Delete permanently? (yes/N): yes
Task deleted.
```

### Profile Structure

**Path shortcuts** in data_path/output_path:
- `~/dir/file` → your home directory
- `@/dir/file` → runtime app root (`TK_APP_ROOT` if set, otherwise packaged app dir / source package dir)
- `~\dir\file` and `@\dir\file` are also accepted (normalized to path separators)
- `./dir/file` or `file` → relative to profile directory
- `/abs/path` → absolute path used as-is

**Note**: Profile file paths passed via `--profile` must be absolute or use `~/` or `@/` (relative profile paths are rejected).

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

**help** - Show available commands
```
tk> help
```

**history (h)** `[--days N] [--working-days N]` - Show completed/cancelled tasks
```
tk> h                      # all history
tk> h --days 7            # last 7 calendar days
tk> h --working-days 5    # last 5 days with tasks
```

**today (t)** - Show today's handled tasks
**yesterday (y)** - Show yesterday's handled tasks
**recent (r)** - Show last 3 working days

### Completing Tasks

**done (d)** `<num>` - Mark as done (with interactive prompts)
```
tk> d 1
```

**cancel (c)** `<num>` - Mark as cancelled
```
tk> c 2
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

- **Use help command:** Type `help` in REPL to see available commands
- **Numbers reset:** After any command that changes state, run `list` or `history` again to get fresh numbers
- **Use shortcuts:** `a`, `l`, `d`, `c`, `e` for speed
- **Ctrl+C cancels:** Interactive prompts (done/cancel/delete) can be cancelled anytime
- **Update after handling:** Use `note <num> [<text>]` and `date <num> <YYYY-MM-DD>` on handled tasks
- **Unknown handled date:** If a handled task has no subjective date (from manual JSON edits), it appears under `unknown` in both `history` output and `TODO.md`
- **No duplicate checking:** Intentional design choice - just cancel or delete if needed
- **Delete is rare:** Use `cancel` for tasks you won't do; reserve `delete` for mistakes

## Installation for Daily Use

After `uv sync`, you can either:

**Option 1:** Run via uv
```bash
cd /path/to/shared/apps/tk
uv run tk -p ~/my-profile.json
```

**Option 2:** Create an alias
```bash
alias tk='uv run --directory /path/to/shared/apps/tk tk'
tk -p ~/my-profile.json
```

## Troubleshooting

**"Run 'list' or 'history' first" error:** You tried a number-based command without a current list. Run `list`, `history`, `today`, `yesterday`, or `recent` first.

**"Unknown command" error:** Check for typos or unsupported commands. Use `help` in REPL to see valid commands.

**Numbers not working:** Task numbers reset after state-changing commands (add, edit, done, etc). Run `list` again.

**Getting help in REPL:** Type `help` to see command list.

**Debug mode:** Set `TK_DEBUG=1` environment variable for detailed error traces:
```bash
TK_DEBUG=1 tk -p ~/my-profile.json
```

## Advanced Usage

### Manual Data Edits
You can edit tasks.json directly, but:
- Always keep valid JSON structure
- Tasks without `subjective_date` will appear as "unknown" in history
- Running any command will validate and may fail if structure is invalid

### Profile Fields Reference
```json
{
  "data_path": "./tasks.json",       // required
  "output_path": "./TODO.md",        // required
  "timezone": "America/New_York",    // required, IANA format
  "subjective_day_start": "04:00:00",// required, HH:MM:SS or HH:MM
  "auto_sync": true,                 // optional, default: true
  "sync_on_exit": false              // optional, default: false
}
```

## Windows & One-File Packaging Notes

These are current project assumptions, documented for future packaging work:

- Windows `.exe` one-file packaging is not an active goal right now.
- Timezone behavior on Windows is expected to depend on runtime packaging details (for example bundled timezone data); verify during actual packaging/testing.
- `@/` paths map to runtime app root (`TK_APP_ROOT` override supported), so they work in both source and packaged modes when that root is configured as intended.

## License

This project is licensed under the MIT License. See `LICENSE`.

## Support

For bugs or feature requests, open an issue in this repository with:
- your command input
- the exact error/output
- your profile settings (redacted as needed)
