# tk - Implementation Plan

## Project Structure

```
tk/
├── src/
│   └── tk/
│       ├── __init__.py
│       ├── __main__.py          # Entry point for `python -m tk`
│       ├── cli.py               # REPL loop, command parsing
│       ├── profile.py           # Profile loading/creation, path mapping
│       ├── data.py              # Task data operations (load/save JSON)
│       ├── commands.py          # Command handlers (add, list, done, etc.)
│       ├── subjective_date.py   # Subjective day calculation logic
│       └── markdown.py          # TODO.md generation
├── tests/                       # Future tests if needed
├── pyproject.toml
├── README.md
├── WHAT.md
└── HOW.md
```

## Data Models

### Profile (JSON)
```python
{
    "data_path": "~/work/tasks.json",      # Absolute or mapped (~, @)
    "output_path": "~/work/TODO.md",       # Absolute or mapped
    "timezone": "Asia/Tokyo",              # IANA timezone string
    "subjective_day_start": "04:00:00"     # HH:MM or HH:MM:SS
}
```

### Tasks Data (JSON)
```python
{
    "next_id": 5,
    "tasks": [
        {
            "id": 1,
            "text": "task description",
            "status": "pending",           # "pending" | "done" | "declined"
            "created_at": "2026-01-31T10:00:00Z",  # ISO 8601 UTC
            "handled_at": null,            # ISO 8601 UTC or null
            "subjective_date": null,       # "YYYY-MM-DD" or null
            "note": null                   # String or null
        }
    ]
}
```

### Session State (in-memory)
```python
{
    "profile_path": "/absolute/path/to/profile.json",
    "profile": Profile,
    "tasks": TaskData,
    "last_list": [(display_num, task_id), ...]  # For stateless numbering
}
```

## Core Modules

### 1. profile.py

**Responsibilities:**
- Load profile from JSON file
- Create new profile with defaults
- Map relative paths (`~` → home, `@` → app dir)
- Validate profile structure

**Key Functions:**
```python
def map_path(path: str, profile_dir: str) -> str:
    """Map ~, @ prefixes to absolute paths"""
    # ~ → home directory
    # @ → app directory (where pyproject.toml is)
    # Otherwise: treat as absolute

def load_profile(path: str) -> dict:
    """Load and validate profile from JSON"""

def create_profile(path: str) -> dict:
    """Create new profile with defaults:
    - timezone: system timezone
    - subjective_day_start: "04:00:00"
    - data_path: same dir as profile, "tasks.json"
    - output_path: same dir as profile, "TODO.md"
    """

def parse_time(time_str: str) -> tuple[int, int, int]:
    """Parse HH:MM or HH:MM:SS to (hours, minutes, seconds)"""
```

**Edge Cases:**
- Profile file doesn't exist → error, suggest using `new` command
- Invalid JSON → clear error message
- Invalid timezone → error with suggestion
- Invalid time format → error with expected format
- Relative path in profile when loading → map it before use

### 2. data.py

**Responsibilities:**
- Load tasks from JSON
- Save tasks to JSON
- CRUD operations on task list
- Maintain next_id counter

**Key Functions:**
```python
def load_tasks(path: str) -> dict:
    """Load tasks.json, create if doesn't exist"""
    # If file doesn't exist, return {"next_id": 1, "tasks": []}

def save_tasks(path: str, data: dict) -> None:
    """Save tasks to JSON with pretty formatting"""

def add_task(data: dict, text: str) -> int:
    """Add new task, return new task ID"""
    # Assign next_id, increment it, append to tasks

def get_task_by_id(data: dict, task_id: int) -> dict | None:
    """Find task by ID"""

def update_task(data: dict, task_id: int, **updates) -> bool:
    """Update task fields, return success"""

def delete_task(data: dict, task_id: int) -> bool:
    """Remove task from list, return success"""
```

**Edge Cases:**
- tasks.json doesn't exist → create with empty structure
- tasks.json is invalid JSON → error with backup suggestion
- Task ID not found → return None/False
- Deleted tasks leave gaps in IDs → that's fine, IDs never reused

### 3. subjective_date.py

**Responsibilities:**
- Calculate subjective date from UTC timestamp
- Handle timezone conversion
- Apply day-start offset

**Key Functions:**
```python
def calculate_subjective_date(
    utc_timestamp: str,
    timezone: str,
    day_start: str
) -> str:
    """
    Convert UTC timestamp to subjective date (YYYY-MM-DD)

    Algorithm:
    1. Parse UTC timestamp to datetime
    2. Convert to target timezone
    3. Parse day_start to hours/minutes/seconds
    4. If local time < day_start:
       subjective_date = local_date - 1 day
    5. Else:
       subjective_date = local_date
    6. Return as YYYY-MM-DD string
    """

def get_current_subjective_date(timezone: str, day_start: str) -> str:
    """Get current subjective date based on current time"""
```

**Example:**
```
UTC: 2026-01-30T16:00:00Z
Timezone: Asia/Tokyo (UTC+9)
Local: 2026-01-31T01:00:00
Day start: 04:00:00
Local time (01:00) < Day start (04:00)
→ Subjective date: 2026-01-30
```

**Edge Cases:**
- Invalid timezone → raise error
- DST transitions → zoneinfo handles this
- Date line crossing → handled by timezone conversion

### 4. markdown.py

**Responsibilities:**
- Generate TODO.md from task data
- Format task lists with checkboxes
- Group by status and subjective date
- Apply sorting rules

**Key Functions:**
```python
def generate_todo(tasks: list, output_path: str) -> None:
    """
    Generate TODO.md from tasks

    Structure:
    # Tasks

    ## Pending
    - [ ] task text

    ## Done
    ### YYYY-MM-DD (descending dates)
    - [x] task text (note if present)

    ## Declined
    ### YYYY-MM-DD (descending dates)
    - [~] task text (note if present)
    """

def sort_tasks(tasks: list) -> dict:
    """
    Sort tasks into structure for rendering

    Returns:
    {
        "pending": [tasks sorted by created_at asc],
        "done": {
            "2026-01-31": [tasks sorted by handled_at asc],
            "2026-01-30": [tasks sorted by handled_at asc]
        },
        "declined": {
            "2026-01-30": [tasks sorted by handled_at asc]
        }
    }
    """
```

**Formatting:**
- Pending: `- [ ] task text`
- Done: `- [x] task text (note)` if note, else `- [x] task text`
- Declined: `- [~] task text (note)` if note, else `- [~] task text`
- Dates in descending order
- Within date, tasks in ascending order by handled_at

**Edge Cases:**
- No tasks → still generate file with empty sections
- Tasks without subjective_date → skip (shouldn't happen for handled tasks)
- Very long task text → no line wrapping, keep as one line

### 5. commands.py

**Responsibilities:**
- Implement all user commands
- Handle command arguments
- Update session state
- Coordinate between modules

**Commands:**

#### `new <profile_path>`
```python
def cmd_new(profile_path: str) -> None:
    """
    Create new profile
    1. Get system timezone
    2. Create profile with defaults
    3. Save to profile_path
    4. Load it into session
    5. Create empty tasks.json
    """
```

#### `add <text>`
```python
def cmd_add(session: dict, text: str) -> None:
    """
    Add new task
    1. Add task to data (sets created_at to now UTC)
    2. Save tasks.json
    3. Regenerate TODO.md
    4. Show confirmation with task ID
    """
```

#### `list`
```python
def cmd_list(session: dict) -> None:
    """
    List pending tasks
    1. Filter tasks where status == "pending"
    2. Sort by created_at ascending
    3. Display with numbers 1, 2, 3...
    4. Store mapping [(1, task_id), ...] in session.last_list
    5. Clear last_list on next command that's not number-based
    """
```

#### `history [--days N]`
```python
def cmd_history(session: dict, days: int | None) -> None:
    """
    List handled tasks
    1. Filter tasks where status in ["done", "declined"]
    2. If days specified, filter by subjective_date
    3. Group by subjective_date (descending)
    4. Within group, sort by handled_at (ascending)
    5. Display with numbers 1, 2, 3...
    6. Store mapping in session.last_list
    """
```

#### `done <num> [--note "text"] [--date YYYY-MM-DD]`
```python
def cmd_done(session: dict, num: int, note: str | None, date: str | None) -> None:
    """
    Mark task as done
    1. Check session.last_list exists (error if not)
    2. Map num to task_id
    3. If date provided: use it as subjective_date
    4. Else: calculate from current time + profile settings
    5. Update task: status="done", handled_at=now UTC, subjective_date, note
    6. Save tasks.json
    7. Regenerate TODO.md
    8. Clear session.last_list
    """
```

#### `decline <num> [--note "text"] [--date YYYY-MM-DD]`
```python
def cmd_decline(session: dict, num: int, note: str | None, date: str | None) -> None:
    """Same as done but status="declined" """
```

#### `edit <num> <text>`
```python
def cmd_edit(session: dict, num: int, text: str) -> None:
    """
    Edit task text
    1. Check session.last_list exists
    2. Map num to task_id
    3. Update task text
    4. Save tasks.json
    5. Regenerate TODO.md
    6. Clear session.last_list
    """
```

#### `delete <num>`
```python
def cmd_delete(session: dict, num: int) -> None:
    """
    Delete task permanently
    1. Check session.last_list exists
    2. Map num to task_id
    3. Delete task from data
    4. Save tasks.json
    5. Regenerate TODO.md
    6. Clear session.last_list
    """
```

#### `sync`
```python
def cmd_sync(session: dict) -> None:
    """
    Regenerate TODO.md from current data
    Useful if TODO.md was manually deleted or corrupted
    """
```

#### `exit` / `quit`
```python
def cmd_exit() -> None:
    """Exit REPL"""
```

**Stateless Enforcement:**
- Commands that take `<num>`: done, decline, edit, delete
- These require `session.last_list` to exist
- If not, show error: "Run 'list' or 'history' first"
- Any command that doesn't use numbers clears `session.last_list`

### 6. cli.py

**Responsibilities:**
- Main entry point
- REPL loop
- Command parsing
- Session management

**Flow:**
```python
def main():
    """
    1. Parse --profile/-p argument
       If not provided: error, show usage

    2. Load profile (or create with 'new' command)

    3. Initialize session state

    4. Enter REPL loop:
       tk> <command>

    5. Parse command and dispatch to handlers

    6. Handle errors gracefully

    7. Exit on 'exit' or 'quit' command
    """

def parse_command(line: str) -> tuple[str, list, dict]:
    """
    Parse command line into (command, args, kwargs)

    Examples:
    "add foo bar" → ("add", ["foo bar"], {})
    "done 1 --note 'finished'" → ("done", [1], {"note": "finished"})
    "history --days 7" → ("history", [], {"days": 7})
    """
```

**REPL Features:**
- Prompt: `tk> `
- Command history (using readline if available)
- Ctrl-C → catch and continue (don't exit)
- Ctrl-D → exit gracefully
- Empty line → ignore
- Unknown command → show error, continue

**Error Handling:**
- Profile not found → suggest `new` command
- Invalid JSON → show error with file path
- Task not found → clear error message
- Invalid arguments → show command usage
- File I/O errors → show path and error

## Implementation Order

1. **profile.py** - Foundation for everything
   - Path mapping
   - Load/create profile
   - Validate structure

2. **data.py** - Core data operations
   - Load/save tasks
   - CRUD operations
   - Test with sample data

3. **subjective_date.py** - Time logic
   - Implement calculation
   - Test edge cases (DST, date boundaries)

4. **markdown.py** - Output generation
   - Sorting logic
   - Formatting
   - Test with various task states

5. **commands.py** - Business logic
   - Implement each command
   - Wire up modules
   - Handle edge cases

6. **cli.py** - User interface
   - REPL loop
   - Command parsing
   - Session management
   - Error handling

7. **__main__.py** & **__init__.py** - Package setup
   - Entry points
   - Version info

8. **pyproject.toml** - Poetry configuration
   - Dependencies: none (stdlib only)
   - Script entry point

## Testing Approach

**Manual Testing Scenarios:**

1. Profile creation and loading
2. Task CRUD operations
3. Subjective date calculation around day boundaries
4. Stateless number enforcement
5. TODO.md generation with various task states
6. Path mapping (~, @)
7. Error conditions

**Files to Create for Testing:**
- Sample profile: `test-profile.json`
- Sample tasks: `test-tasks.json`
- Verify TODO.md output

## Python Dependencies

**Standard library only:**
- `json` - Data serialization
- `pathlib` - Path handling
- `datetime` - Timestamp handling
- `zoneinfo` - Timezone support (Python 3.9+)
- `argparse` - CLI argument parsing (for --profile)
- `cmd` or manual REPL - Interactive loop
- `readline` - Command history (optional)

**No external dependencies needed.**

## Edge Cases & Error Handling

1. **Profile Issues:**
   - File not found → error with suggestion
   - Invalid JSON → show error, suggest fix
   - Missing required fields → error listing required fields
   - Invalid timezone → suggest valid timezone

2. **Data Issues:**
   - tasks.json corrupted → error, suggest restore from backup
   - Task ID not found → "Task not found"
   - Empty task text → "Task text cannot be empty"

3. **Path Mapping:**
   - @ when app dir can't be determined → error
   - ~ when home can't be determined → error
   - Relative path that looks absolute → use as-is

4. **Time Handling:**
   - Invalid date format in --date → show expected format
   - Future date in --date → allow (user knows what they're doing)
   - Invalid time in subjective_day_start → error with format

5. **Stateless Enforcement:**
   - Number command without list/history → clear error
   - Number out of range → "Invalid task number"
   - List changed between commands → that's why we're stateless

6. **File I/O:**
   - Can't write TODO.md → show path and error
   - Can't write tasks.json → critical error
   - Directory doesn't exist → create it

## Output Examples

### List Output
```
tk> list
1. [ ] implement user authentication
2. [ ] refactor database layer
3. [ ] practice writing the what
```

### History Output
```
tk> history
2026-01-31
  1. [x] commit initial docs
  2. [x] minimal .gitignore (added to repos)

2026-01-30
  3. [x] beyond compare on macbook
  4. [~] add Redis caching (using in-memory instead)
```

### Success Messages
```
tk> add "new task"
Task #4 added.

tk> done 1 --note "finished"
Task #1 marked as done.

tk> new ~/work/profile.json
Profile created: /Users/nao7sep/work/profile.json
```

### Error Messages
```
tk> done 1
Error: Run 'list' or 'history' first

tk> edit 99 "text"
Error: Invalid task number

tk> add
Error: Usage: add <text>

tk> done 1 --date invalid
Error: Invalid date format. Expected: YYYY-MM-DD
```

## Notes

- Keep it simple - no fancy features initially
- Use stdlib only - no external dependencies
- Clear error messages - user shouldn't be confused
- Auto-generate TODO.md after every change - always in sync
- Subjective date is immutable once set - data integrity
- IDs never reused - gaps are fine
- Profile is session-scoped - can run multiple tk instances with different profiles

## Future Enhancements (Out of Scope for v1)

- Multiple profiles management
- Import/export features
- Task search/filtering
- Undo functionality
- Task templates
- Recurring tasks
- Task dependencies
- Rich formatting in terminal
- Config file for default profile

Focus on core functionality first. Ship it. Use it. Iterate based on real pain points.
