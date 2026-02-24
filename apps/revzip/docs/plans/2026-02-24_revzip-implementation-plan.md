# revzip

Implementation plan generated from conversation on 2026-02-24.

## Overview
`revzip` is a simple Python REPL CLI that snapshots a source directory into zip archives and restores a chosen snapshot to an exact historical state. Each snapshot is stored as a zip file plus a same-base metadata JSON file in the destination directory.

## Requirements
### Core Behavior
- Require `--source` and `--dest` at startup; allow optional `--ignore` regex file path.
- Enter REPL immediately after successful startup.
- REPL supports only menu choices: `1. Archive`, `2. Extract`, `3. Exit` (no free-typed commands).
- Always show menu options; validate operation feasibility only when user selects an action.
- Use `uv` for project/runtime workflow.
- Provide `README.md` and `.command` helper script(s) for trivial tasks.

### Archive Flow
- Require a non-empty comment; if empty, abort archive and return to menu.
- Use zip filename format `YYYY-MM-DD_HH-MM-SS_user-comment.zip` in local time.
- Save metadata as same base name with `.json`.
- Sanitize comment for filename only:
- replace spaces and reserved characters `/ \ : * ? " < > |` with `-`
- keep UTF-8/CJK characters
- Keep the original unsanitized comment in metadata.
- Apply built-in default ignores for `.git`, `.DS_Store`, `Thumbs.db`, and `desktop.ini`.
- If `--ignore` is provided, match regex patterns against `raw_source_argument + "/" + relative_path` (do not resolve `--source` to absolute before regex matching).
- Archive regular files and empty directories.
- Store two separate sorted metadata arrays: archived files and empty directories.
- If both arrays are empty, do not create zip/metadata files.
- Report archived file count to the user.

### Extract Flow
- Build selectable snapshots from metadata JSON files in destination.
- Sort snapshots descending by UTC timestamp (latest first).
- Display numbered list with left-padded index width and `|` separators.
- Require numeric selection and exact `yes` confirmation before restore.
- Verify zip integrity before deleting/restoring source directory.
- Restore exact state by removing current source contents, recreating source directory, and extracting snapshot.

### Timestamps And Formatting
- User-facing datetime format: local `YYYY-MM-DD HH:MM:SS`.
- Internal datetime format: UTC ISO 8601 with microseconds and `Z`.
- Any UTC-related variable/key name must include `utc`.
- Use `-` within semantic groups and `_` between semantic groups.
- Prefer `|` as display separator.

### Models, Constants, And Error Handling
- Use dataclasses for structured data passed across layers (no raw dict data passing between components).
- Create `constants.py` for literal values only; keep user-facing messages near usage sites.
- Raise exceptions in lower layers and catch them at CLI boundary for clean user messages.
- During snapshot discovery, visibly warn ("scream") when metadata JSON is invalid or corresponding zip is missing.
- Ensure UTF-8 file names are handled correctly in zip archives and extraction.

### Project Context Alignment
- Before final structure is finalized, check `autopage` and `booktrans` directory/style conventions and align where sensible.

## Architecture
- CLI/REPL layer:
- Parse args, run menu loop, gather user selections/comments, render snapshot list.
- Catch boundary exceptions and print user-facing failures.
- Business logic layer:
- `archive_manager` handles ignore application, traversal, timestamp/comment processing, and snapshot creation.
- `extract_manager` handles snapshot discovery, ordering, selection validation, safety checks, and restore orchestration.
- Data/file layer:
- Dataclasses for snapshot metadata and extract list rows.
- Zip/JSON readers/writers and filesystem utilities for traversal, empty-dir detection, and restore operations.
- Constants module:
- Date formats, reserved char set, default ignore sets, menu constants, and filename templates.

## Implementation Steps
1. Scaffold project at `/shared/apps/revzip` with `uv` configuration and base package structure.
2. Add `constants.py` and dataclasses for metadata and extract list entries.
3. Implement traversal utilities to collect files and empty directories with default ignore handling.
4. Implement optional regex ignore loading and matching using raw source argument plus relative path.
5. Implement archive workflow: mandatory comment, filename sanitization, local/UTC timestamps, zip writing, metadata writing, zero-entry abort.
6. Implement snapshot discovery/parsing from metadata JSON and descending UTC sorting.
7. Implement extract workflow: list rendering with padded indices and `|`, selection parsing, exact `yes` confirmation, zip integrity verification, destructive restore.
8. Wire CLI argument parsing and REPL control flow, with boundary exception handling and clear messages.
9. Add `.command` helper script(s) for common runs with placeholder path editing.
10. Write `README.md` with usage, safety behavior, ignore semantics, timestamp formats, and restore caveats.
11. Validate behavior with tests/manual checks for UTF-8, empty directories, regex matching semantics, and invalid/orphaned snapshot handling.

## Open Questions
- Should restore attempt trash-first behavior (for example via `send2trash`) or always delete directly after zip verification?
- When invalid/orphaned snapshot metadata is found, should extract continue with warnings or block until cleanup?
- Which exact `.command` scripts are required (single launcher vs multiple task-specific launchers)?
- How strict should alignment to `autopage`/`booktrans` be (layout only vs naming/test conventions)?
