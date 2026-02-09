# Test Plan for tk

Following the testing style of poly-chat project.

## Overview

This test plan covers all modules in tk with a focus on:
- Critical validation logic (data integrity)
- Command execution and routing
- State management
- Interactive prompts (mocked)
- Edge cases and error handling

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_data.py             # Data module tests
├── test_validation.py       # Validation tests
├── test_commands.py         # Command logic tests
├── test_dispatcher.py       # Command dispatcher tests
├── test_prompts.py          # Interactive prompts tests
├── test_profile.py          # Profile management tests
├── test_session.py          # Session state tests
├── test_subjective_date.py  # Date calculation tests
├── test_markdown.py         # TODO.md generation tests
└── test_repl.py             # REPL parsing tests
```

---

## Test Dependencies

Add to `pyproject.toml`:

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-mock = "^3.12.0"
freezegun = "^1.4.0"  # For time-dependent tests
```

---

## 1. conftest.py - Shared Fixtures

### Fixtures to Create

```python
@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""

@pytest.fixture
def sample_profile(temp_dir):
    """Create sample profile JSON for testing."""

@pytest.fixture
def sample_tasks_data():
    """Create sample tasks data structure."""

@pytest.fixture
def sample_session(sample_profile, sample_tasks_data):
    """Create initialized Session object."""

@pytest.fixture
def empty_session():
    """Create empty Session for testing error cases."""

@pytest.fixture
def mock_time():
    """Freeze time for consistent date/time tests."""
```

---

## 2. test_data.py - Data Module Tests

### Class: TestLoadTasks
- `test_load_tasks_nonexistent_file()` - Returns empty structure
- `test_load_tasks_creates_directory()` - Creates parent directory
- `test_load_tasks_valid_file()` - Loads valid JSON
- `test_load_tasks_invalid_json()` - Raises ValueError
- `test_load_tasks_missing_tasks_key()` - Raises ValueError

### Class: TestValidateTasksStructure
- `test_validate_empty_tasks()` - Accepts empty array
- `test_validate_valid_tasks()` - Accepts well-formed tasks
- `test_validate_missing_tasks_key()` - Raises ValueError
- `test_validate_tasks_not_array()` - Raises ValueError
- `test_validate_missing_required_fields()` - Raises ValueError for each field
- `test_validate_invalid_status()` - Raises ValueError
- `test_validate_task_not_dict()` - Raises ValueError

### Class: TestSaveTasks
- `test_save_tasks_creates_directory()` - Creates parent directory
- `test_save_tasks_writes_valid_json()` - Writes correctly
- `test_save_tasks_preserves_encoding()` - UTF-8 encoding works

### Class: TestAddTask
- `test_add_task_returns_index()` - Returns correct index
- `test_add_task_structure()` - Creates correct task structure
- `test_add_task_status_pending()` - Status is "pending"
- `test_add_task_nulls_set_correctly()` - Handled fields are null
- `test_add_task_timestamp_utc()` - Timestamp is UTC

### Class: TestUpdateTask
- `test_update_task_valid_field()` - Updates allowed field
- `test_update_task_invalid_field()` - Raises ValueError
- `test_update_task_nonexistent_index()` - Returns False
- `test_update_task_multiple_fields()` - Updates multiple fields
- `test_update_task_invalid_field_mixed()` - Rejects mixed valid/invalid

### Class: TestDeleteTask
- `test_delete_task_valid_index()` - Removes task and returns True
- `test_delete_task_invalid_index()` - Returns False
- `test_delete_task_shifts_indices()` - Subsequent indices shift

### Class: TestGroupHandledTasks
- `test_group_handled_tasks_empty()` - Handles empty list
- `test_group_handled_tasks_by_date()` - Groups by subjective_date
- `test_group_handled_tasks_unknown()` - Handles missing dates
- `test_group_handled_tasks_sort_dates_desc()` - Dates descending
- `test_group_handled_tasks_sort_within_date()` - Tasks by handled_at asc

---

## 3. test_validation.py - Validation Tests

### Class: TestValidateDateFormat
- `test_validate_date_valid()` - Accepts YYYY-MM-DD
- `test_validate_date_invalid_format()` - Rejects wrong format
- `test_validate_date_invalid_month()` - Rejects 2026-13-01
- `test_validate_date_invalid_day()` - Rejects 2026-02-30
- `test_validate_date_leap_year()` - Handles leap years correctly
- `test_validate_date_empty_string()` - Rejects empty string

---

## 4. test_commands.py - Command Logic Tests

### Class: TestListPendingData
- `test_list_pending_data_empty()` - Returns empty items
- `test_list_pending_data_multiple_tasks()` - Returns correct display_num mapping
- `test_list_pending_data_sorts_by_created_at()` - Sorts chronologically
- `test_list_pending_data_filters_handled()` - Excludes done/cancelled

### Class: TestListHistoryData
- `test_list_history_data_empty()` - Returns empty groups
- `test_list_history_data_days_filter()` - Filters by days
- `test_list_history_data_working_days_filter()` - Filters by working days
- `test_list_history_data_specific_date_filter()` - Filters by specific date
- `test_list_history_data_multiple_filters_error()` - Raises ValueError

### Class: TestCmdAdd
- `test_cmd_add_creates_task()` - Creates task
- `test_cmd_add_empty_text_error()` - Raises ValueError
- `test_cmd_add_syncs_if_auto()` - Calls sync when auto_sync true
- `test_cmd_add_no_sync_if_disabled()` - Skips sync when auto_sync false

### Class: TestCmdDone
- `test_cmd_done_marks_task()` - Sets status to "done"
- `test_cmd_done_sets_handled_at()` - Sets timestamp
- `test_cmd_done_sets_subjective_date()` - Uses provided or default date
- `test_cmd_done_invalid_index_error()` - Raises ValueError

### Class: TestCmdCancel
- `test_cmd_cancel_marks_task()` - Sets status to "cancelled"
- `test_cmd_cancel_with_note()` - Saves note

### Class: TestCmdEdit
- `test_cmd_edit_changes_text()` - Updates text
- `test_cmd_edit_empty_text_error()` - Raises ValueError
- `test_cmd_edit_invalid_index_error()` - Raises ValueError

### Class: TestCmdDelete
- `test_cmd_delete_without_confirm()` - Returns "Deletion cancelled"
- `test_cmd_delete_with_confirm()` - Deletes task
- `test_cmd_delete_invalid_index_error()` - Raises ValueError

### Class: TestCmdNote
- `test_cmd_note_sets_note()` - Sets note
- `test_cmd_note_removes_note()` - Removes note when None
- `test_cmd_note_invalid_index_error()` - Raises ValueError

### Class: TestCmdDate
- `test_cmd_date_changes_date()` - Updates subjective_date
- `test_cmd_date_invalid_format_error()` - Raises ValueError
- `test_cmd_date_pending_task_error()` - Raises ValueError

### Class: TestCmdSync
- `test_cmd_sync_generates_markdown()` - Calls generate_todo

---

## 5. test_dispatcher.py - Command Dispatcher Tests

### Class: TestCommandAliases
- `test_resolve_alias_a()` - "a" → "add"
- `test_resolve_alias_l()` - "l" → "list"
- `test_resolve_alias_all()` - Test all aliases
- `test_resolve_unknown_unchanged()` - Unknown passes through

### Class: TestNormalizeArgs
- `test_normalize_args_add()` - Joins multiple args
- `test_normalize_args_edit_converts_int()` - Converts first arg to int
- `test_normalize_args_done_converts_int()` - Converts first arg to int
- `test_normalize_args_invalid_int()` - Leaves non-int unchanged

### Class: TestCommandRegistry
- `test_registry_has_all_commands()` - All 14 commands present
- `test_registry_handlers_have_executor()` - All have executor function
- `test_registry_handlers_have_usage()` - All have usage string
- `test_list_commands_dont_clear_list()` - list/history/today/yesterday/recent

### Class: TestExecuteCommand
- `test_execute_command_add()` - Executes add command
- `test_execute_command_list()` - Executes list command
- `test_execute_command_done()` - Executes done command
- `test_execute_command_unknown()` - Raises ValueError
- `test_execute_command_exit()` - Returns "EXIT"
- `test_execute_command_clears_list()` - Clears mapping after mutation

---

## 6. test_prompts.py - Interactive Prompts Tests

### Class: TestCollectDonePrompts
- `test_collect_done_prompts_with_note(monkeypatch)` - Collects note
- `test_collect_done_prompts_skip_note(monkeypatch)` - Handles empty note
- `test_collect_done_prompts_with_date(monkeypatch)` - Collects custom date
- `test_collect_done_prompts_default_date(monkeypatch)` - Uses default
- `test_collect_done_prompts_cancelled(monkeypatch)` - Returns "CANCELLED"
- `test_collect_done_prompts_provided_note()` - Uses provided note
- `test_collect_done_prompts_provided_date()` - Uses provided date

### Class: TestCollectDeleteConfirmation
- `test_collect_delete_confirmation_yes(monkeypatch)` - Returns True
- `test_collect_delete_confirmation_no(monkeypatch)` - Returns False
- `test_collect_delete_confirmation_empty(monkeypatch)` - Returns False

---

## 7. test_profile.py - Profile Management Tests

### Class: TestMapPath
- `test_map_path_tilde_with_subpath()` - Maps ~/path
- `test_map_path_tilde_alone()` - Maps ~
- `test_map_path_at_with_subpath()` - Maps @/path
- `test_map_path_at_alone()` - Maps @
- `test_map_path_absolute()` - Passes through absolute
- `test_map_path_relative()` - Resolves relative to profile_dir

### Class: TestParseTime
- `test_parse_time_hh_mm()` - Parses 04:00
- `test_parse_time_hh_mm_ss()` - Parses 04:00:00
- `test_parse_time_invalid_format()` - Raises ValueError
- `test_parse_time_invalid_range()` - Raises ValueError

### Class: TestValidateProfile
- `test_validate_profile_valid()` - Accepts valid profile
- `test_validate_profile_missing_field()` - Raises ValueError
- `test_validate_profile_invalid_time()` - Raises ValueError
- `test_validate_profile_empty_timezone()` - Raises ValueError

### Class: TestLoadProfile
- `test_load_profile_nonexistent()` - Raises FileNotFoundError
- `test_load_profile_invalid_json()` - Raises JSONDecodeError
- `test_load_profile_valid()` - Loads correctly
- `test_load_profile_maps_paths()` - Maps data_path and output_path
- `test_load_profile_sets_defaults()` - Sets auto_sync and sync_on_exit

### Class: TestCreateProfile
- `test_create_profile_creates_file()` - Creates file
- `test_create_profile_creates_directory()` - Creates parent dir
- `test_create_profile_detects_timezone()` - Uses system timezone
- `test_create_profile_defaults()` - Sets correct defaults
- `test_create_profile_fallback_to_utc(monkeypatch)` - Falls back to UTC

---

## 8. test_session.py - Session State Tests

### Class: TestSessionCreation
- `test_create_minimal_session()` - Creates with defaults
- `test_session_defaults()` - Checks default values

### Class: TestSessionRequireMethods
- `test_require_profile_with_profile()` - Returns profile
- `test_require_profile_without_profile()` - Raises ValueError
- `test_require_tasks_with_tasks()` - Returns tasks
- `test_require_tasks_without_tasks()` - Raises ValueError

### Class: TestSessionListMapping
- `test_set_last_list()` - Sets mapping
- `test_clear_last_list()` - Clears mapping
- `test_resolve_array_index()` - Resolves display_num to index
- `test_resolve_array_index_no_list()` - Raises ValueError
- `test_resolve_array_index_invalid_num()` - Raises ValueError

### Class: TestSessionTaskRetrieval
- `test_get_task_by_display_number()` - Gets correct task
- `test_get_task_by_display_number_invalid()` - Raises ValueError

---

## 9. test_subjective_date.py - Date Calculation Tests

### Class: TestCalculateSubjectiveDate
- `test_calculate_before_day_start()` - Returns previous day
- `test_calculate_after_day_start()` - Returns same day
- `test_calculate_at_day_start_boundary()` - Boundary case
- `test_calculate_with_timezone_offset()` - Handles timezones
- `test_calculate_invalid_timezone()` - Raises ValueError

### Class: TestGetCurrentSubjectiveDate
- `test_get_current_subjective_date(mock_time)` - Returns correct date

---

## 10. test_markdown.py - TODO.md Generation Tests

### Class: TestGenerateTodo
- `test_generate_todo_empty()` - Generates "No pending tasks"
- `test_generate_todo_pending_only()` - Generates pending section
- `test_generate_todo_with_history()` - Generates history section
- `test_generate_todo_creates_directory()` - Creates parent dir
- `test_generate_todo_format()` - Correct markdown format
- `test_generate_todo_dates_descending()` - History dates descending
- `test_generate_todo_tasks_within_date()` - Tasks by handled_at
- `test_generate_todo_with_notes()` - Includes notes with =>
- `test_generate_todo_status_emoji()` - ✅ done, ❌ cancelled

---

## 11. test_repl.py - REPL Parsing Tests

### Class: TestParseCommand
- `test_parse_command_empty()` - Returns empty cmd
- `test_parse_command_simple()` - Parses "add text"
- `test_parse_command_with_flags()` - Parses --note --date
- `test_parse_command_flag_int_value()` - Converts int values
- `test_parse_command_flag_boolean()` - Boolean flags
- `test_parse_command_no_flag_commands()` - add/edit/note special handling

### Class: TestPrepareInteractiveCommand
- Test with monkeypatch for input()
- `test_prepare_done_prompts_collected()` - Collects prompts
- `test_prepare_done_ctrl_c()` - Handles Ctrl+C
- `test_prepare_delete_confirmation()` - Collects confirmation
- `test_prepare_no_interaction_for_list()` - Passes through

---

## Critical Test Priorities

### P0 - Must Have (Data Safety)
1. ✅ Data validation tests (test_data.py - TestValidateTasksStructure)
2. ✅ Field validation tests (test_data.py - TestUpdateTask)
3. ✅ Date validation tests (test_validation.py)
4. ✅ Profile validation tests (test_profile.py)

### P1 - Should Have (Core Functionality)
1. Command execution tests (test_commands.py)
2. Dispatcher registry tests (test_dispatcher.py)
3. Session state tests (test_session.py)
4. Subjective date tests (test_subjective_date.py)

### P2 - Nice to Have (UI/UX)
1. Prompt tests (test_prompts.py)
2. REPL parsing tests (test_repl.py)
3. Markdown generation tests (test_markdown.py)

---

## Test Coverage Goals

- **Critical modules (data, validation, commands):** 90%+
- **Core modules (dispatcher, session, profile):** 80%+
- **Support modules (prompts, repl, markdown):** 70%+

---

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/tk --cov-report=html

# Run specific test file
poetry run pytest tests/test_data.py

# Run specific test class
poetry run pytest tests/test_data.py::TestValidateTasksStructure

# Run specific test
poetry run pytest tests/test_data.py::TestValidateTasksStructure::test_validate_missing_tasks_key

# Run with verbose output
poetry run pytest -v

# Run with debug output
poetry run pytest -vv

# Run tests matching pattern
poetry run pytest -k "validate"
```

---

## Next Steps

1. ✅ Create test plan (this file)
2. ⬜ Set up pytest in pyproject.toml
3. ⬜ Create conftest.py with fixtures
4. ⬜ Implement P0 tests (data safety)
5. ⬜ Implement P1 tests (core functionality)
6. ⬜ Implement P2 tests (UI/UX)
7. ⬜ Run coverage analysis
8. ⬜ Add CI/CD integration (optional)
