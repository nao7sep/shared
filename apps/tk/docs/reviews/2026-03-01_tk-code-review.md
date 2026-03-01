# tk Code Review

Date: 2026-03-01

Output directory checked for collisions:
- `docs/reviews/`
- Existing files: `2026-02-28_dict-to-model-migration.md`, `2026-02-28_tk-commit-843cf369-review.md`

## Findings

### 1. `init` can silently destroy an existing profile and its generated task files

Files:
- `src/tk/profile.py:197-224`
- `src/tk/cli.py:68-86`

Why this is a bug:
- `create_profile()` always opens the target profile with `"w"` and never checks whether the file already exists.
- The `init` flow then immediately writes an empty `TaskStore` to `prof.data_path` and regenerates `prof.output_path`.
- Because the default profile points to `./tasks.json` and `./TODO.md`, re-running `tk init --profile <existing-profile>` can wipe the existing profile, replace the task database with an empty one, and overwrite the generated markdown without any confirmation.

Suggested fix:
- Fail fast when the target profile already exists.
- If overwrite support is desired, require an explicit `--force` flag and keep the destructive behavior behind that flag.

### 2. `done` and `cancel` can mutate already-handled history entries

Files:
- `src/tk/session.py:38-47`
- `src/tk/dispatcher.py:102-113`
- `src/tk/repl.py:101-128`
- `src/tk/commands.py:191-239`

Why this is a bug:
- Task-number resolution is shared across both pending and history views through `Session.last_list`.
- After `history`, `today`, `yesterday`, or `recent`, `done 1` / `cancel 1` resolves against a handled task instead of a pending one.
- `_handle_task()` does not verify that the selected task is still pending, so it overwrites `status`, `handled_utc`, `subjective_date`, and `note` on an already-handled task.
- This lets a user accidentally rewrite task history simply because the last numbered view was a history screen.

Suggested fix:
- Reject `done` / `cancel` unless the target task is `pending`.
- Alternatively, keep separate mappings for pending-task commands versus history-only commands such as `note` and `date`.

### 3. Profile loading does not validate field types, which causes silent misconfiguration and raw type errors

Files:
- `src/tk/profile.py:109-136`
- `src/tk/profile.py:172-177`
- `src/tk/models.py:163-172`

Why this is a bug:
- `validate_profile()` checks presence and a few value constraints, but it never verifies that `data_path`, `output_path`, `auto_sync`, or `sync_on_exit` have the expected types.
- `Profile.from_dict()` then coerces booleans with `bool(...)`, so a JSON value like `"false"` becomes `True`.
- Non-string path values are passed into `map_path()`, which expects a string and can raise a raw `TypeError` instead of a `ConfigError`.
- Since the profile is user-edited JSON, these are common input mistakes that should be rejected precisely rather than misinterpreted.

Suggested fix:
- Extend `validate_profile()` to enforce exact types for every supported field.
- Parse booleans without coercion and raise `ConfigError` on invalid types.

### 4. `sync_on_exit` failures are outside the REPL error boundary

Files:
- `src/tk/repl.py:149-202`
- `src/tk/cli.py:132-136`

Why this is a bug:
- The REPL loop catches `AppError` and unexpected exceptions while processing commands, but the final `sync_on_exit` write happens after the loop exits.
- If `markdown.generate_todo()` fails there because of an I/O problem, the exception is not caught in `repl()` or `cli.main()`.
- The result is an unhandled traceback during normal shutdown, which violates the app's own error-handling boundary pattern.

Suggested fix:
- Wrap the exit-sync block in `repl()` with the same user-facing error handling used inside the loop, or catch and report it from `cli.main()`.
