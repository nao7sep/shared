# revzip

Implementation plan generated from conversation on 2026-02-25.

## Overview
`revzip` is an interactive Python CLI that snapshots a source directory into timestamped zip files and restores a selected snapshot back to an exact directory state. Each snapshot is stored as a zip file plus a same-base metadata JSON file in the destination directory.

## Requirements
### Core Behavior
- Require `--source` and `--dest` at startup.
- Allow optional `--ignore` (path to regex pattern file).
- Enter REPL after startup validation.
- REPL allows only menu choices:
  - `1. Archive`
  - `2. Extract`
  - `3. Exit`
- Keep output plain text only (no colors).
- Use `uv` for dependency/runtime workflow.
- Provide `README.md` and `.command` helper scripts.

### Path Mapping And Argument Validation
- Do not resolve any path from CWD.
- Accept path inputs only when they are:
  - absolute paths
  - `~`-mapped paths
  - `@`-mapped paths (app root mapped)
- Reject pure relative paths for `--source`, `--dest`, and `--ignore`.
- Reject input containing NUL (`\0`).
- Apply Unicode normalization (NFD -> NFC) before mapping checks.
- Reject Windows rooted-but-not-fully-qualified forms (for example `\temp`, `C:temp`).
- Require `--source` and `--dest` not to overlap (same path, ancestor, or descendant): hard fail.
- If `--dest` does not exist, create it.
- If `--dest` exists and is not a directory, fail.

### Archive Flow
- Prompt for archive comment at archive action time.
- Comment must contain at least one visible character after `strip()`; otherwise abort archive action.
- Keep trimmed comment in metadata as-is (multiline content allowed).
- Filename sanitization applies only to filename segment:
  - replace spaces, line breaks, and reserved filename characters (`/ \ : * ? " < > |`) with `-`
  - merge consecutive replacement runs to a single `-`
  - keep UTF-8/CJK characters
- Snapshot filename format:
  - `{YYYY-MM-DD}_{HH-MM-SS}_{sanitized-comment}.zip` (local time for filename)
- Metadata filename uses same base with `.json`.
- If target `.zip` or `.json` already exists (same-second collision), abort with error (no suffixing).
- Apply default ignores: `.git`, `.DS_Store`, `Thumbs.db`, `desktop.ini`.
- Skip symlinks and emit warnings.
- Include regular files and empty directories.
- If ignore regex matches a directory path, prune subtree and treat as non-existent.
- Zip entry paths must be source-relative and must not include the source directory name.
- Zip entry names must use `/` separators.
- Metadata stores two sorted arrays:
  - archived file paths
  - empty directory paths
- Metadata path arrays should use platform-native separators.
- If both arrays are empty, do not create zip or metadata.
- Print archived file count.

### Ignore Rules
- Ignore file format:
  - one regex pattern per line
  - trim each line
  - skip empty lines
  - skip lines beginning with `#`
- For matching, use `re.search` with no auto-added `^` or `$`.
- Match target string must be exactly:
  - `raw_source_argument + "/" + relative_path`
- Matching uses the raw `--source` argument form, not normalized absolute source path.

### Extract Flow
- Discover candidate snapshots from metadata JSON files in destination.
- For each metadata file:
  - if JSON is invalid, warn loudly and continue
  - if corresponding zip is missing, warn loudly and continue
- Build selectable list only from valid metadata+zip pairs.
- Sort selectable snapshots by `created_utc` descending (latest first).
- Render selectable list with:
  - left-padded numeric index width
  - `|` separators
- Require numeric selection.
- Require exact `yes` confirmation before restore.
- Verify zip integrity before destructive restore.
- Restore exact state by deleting current source contents, recreating source directory, and extracting selected zip.

### Timestamps And Naming
- Internal timestamp format: UTC ISO 8601 with microseconds and `Z`.
- Any UTC key/variable names must include `utc`.
- User-facing datetime format: local `YYYY-MM-DD HH:MM:SS` with no timezone marker by default.
- Filenames use `_` between semantic groups and `-` within semantic groups.

### Data Modeling And Error Handling
- Use dataclasses for structured data across layers.
- Do not pass raw dicts between components.
- `constants.py` is for literal values only.
- User-facing messages stay near usage sites (UI layer/services as appropriate).
- Lower layers raise typed exceptions.
- CLI boundary catches exceptions and prints clear user-facing errors.

### Project Layout And Tooling Alignment
- Align operational structure with existing local Python apps:
  - `src/`, `tests/`, `scripts/`, `docs/plans/`
  - `pyproject.toml` with `uv_build`
  - entry point via `[project.scripts]`
  - `.command` wrappers for install/run/test/clean
- Do not copy concern boundaries from existing apps; use Revzip-specific separation.

## Architecture
### Module Boundaries
- `src/revzip/cli.py`
  - Parse args, run startup validation, install top-level error boundary.
- `src/revzip/repl.py`
  - Menu loop, input collection, action dispatch (`archive`, `extract`, `exit`).
- `src/revzip/presenters.py`
  - Menu rendering, snapshot table rendering, warning/error prefix formatting.
- `src/revzip/archive_service.py`
  - Archive orchestration: comment validation, traversal invocation, snapshot artifact creation.
- `src/revzip/extract_service.py`
  - Extract orchestration: discovery, ordering, selection validation, restore execution.
- `src/revzip/snapshot_catalog_service.py`
  - Metadata discovery, parse/validation, warning generation, valid snapshot list building.
- `src/revzip/path_mapping.py`
  - Path mapping/validation policy (`~`, `@`, absolute-only acceptance, rejection cases).
- `src/revzip/ignore_rules.py`
  - Ignore file parsing and runtime regex matcher compilation/execution.
- `src/revzip/comment_sanitizer.py`
  - Comment validation and filename-segment sanitization.
- `src/revzip/timestamps.py`
  - UTC/internal timestamp generation+parse and local display/filename timestamp formatting.
- `src/revzip/fs_gateway.py`
  - Filesystem traversal, empty-dir detection, source clearing/recreation, symlink handling.
- `src/revzip/zip_gateway.py`
  - Zip write/verify/extract, entry-name normalization, duplicate-entry safety checks.
- `src/revzip/metadata_gateway.py`
  - Metadata JSON serialization/deserialization.
- `src/revzip/models.py`
  - Dataclasses only.
- `src/revzip/constants.py`
  - Literal constants only.
- `src/revzip/errors.py`
  - Typed exceptions for policy/validation/io/workflow failures.

### Dataclass Models
- `ResolvedPaths`
  - `source_arg_raw`, `source_dir_abs`, `dest_arg_raw`, `dest_dir_abs`, `ignore_arg_raw`, `ignore_file_abs`
- `IgnoreRuleSet`
  - `patterns_raw`, `compiled_patterns`
- `ArchiveInventory`
  - `archived_files_rel`, `empty_directories_rel`, `skipped_symlinks_rel`
- `SnapshotMetadata`
  - `created_utc`, `created_at`, `comment`, `comment_filename_segment`, `zip_filename`, `archived_files`, `empty_directories`
- `SnapshotRecord`
  - `metadata_path`, `zip_path`, `created_utc`, `created_at`, `comment`, `archived_file_count`, `empty_directory_count`
- `SnapshotWarning`
  - `metadata_path`, `warning_code`, `message`
- `ArchiveResult`
  - `zip_path`, `metadata_path`, `archived_file_count`, `empty_directory_count`, `created_utc`
- `RestoreResult`
  - `selected_zip_path`, `restored_file_count`, `restored_empty_directory_count`

### Data Flow
1. `cli.py` resolves and validates startup paths through `path_mapping.py`.
2. `repl.py` collects user action and delegates to `archive_service.py` or `extract_service.py`.
3. Archive path:
   - `archive_service.py` -> `ignore_rules.py` + `fs_gateway.py` traversal -> `zip_gateway.py` + `metadata_gateway.py`.
4. Extract path:
   - `extract_service.py` -> `snapshot_catalog_service.py` -> selection/confirmation -> `zip_gateway.py` verify -> `fs_gateway.py` clear/recreate -> `zip_gateway.py` extract.
5. Exceptions bubble up to `cli.py`, which formats user-facing failures.

## Implementation Steps
1. Project scaffolding
   - [ ] Create `src/revzip`, `tests`, `scripts`, and docs plan baseline.
   - [ ] Add `pyproject.toml` using `uv_build`, script entry point, and dev group.
   - [ ] Add package entry files (`__init__.py`, `__main__.py`).

2. Constants, errors, and models
   - [ ] Define literal constants in `constants.py`.
   - [ ] Define typed exceptions in `errors.py`.
   - [ ] Define dataclasses in `models.py` (no raw dict contracts).

3. Path mapping/validation subsystem
   - [ ] Implement path mapping policy from spec (`~`, `@`, absolute-only, rejection cases).
   - [ ] Implement overlap checks for `--source` vs `--dest`.
   - [ ] Implement destination existence/type checks and creation behavior.

4. Ignore rules subsystem
   - [ ] Implement ignore file line parsing (trim, blank/# skip).
   - [ ] Compile regex rules with robust error reporting.
   - [ ] Implement `re.search` matching over `raw_source_arg + "/" + relative_path`.

5. Traversal and inventory collection
   - [ ] Implement recursive traversal from source root.
   - [ ] Apply default ignores and optional regex ignores.
   - [ ] Skip symlinks with warnings.
   - [ ] Collect sorted regular-file and empty-directory relative path lists.

6. Archive output pipeline
   - [ ] Implement comment validation and filename-segment sanitization.
   - [ ] Implement local filename timestamp and internal `created_utc`.
   - [ ] Implement collision check for same-base `.zip`/`.json`.
   - [ ] Implement zip writing with source-relative entry names and duplicate-entry guard.
   - [ ] Implement metadata JSON writing.
   - [ ] Implement zero-inventory no-op behavior.

7. Snapshot discovery and validation
   - [ ] Implement metadata file discovery in destination.
   - [ ] Parse metadata into dataclasses.
   - [ ] Validate corresponding zip presence.
   - [ ] Collect loud warnings for invalid/orphaned entries while preserving valid list.
   - [ ] Sort valid records by `created_utc` descending.

8. Restore pipeline
   - [ ] Implement list rendering with padded index and `|` separators.
   - [ ] Implement numeric selection parsing and exact `yes` confirmation.
   - [ ] Verify zip integrity before destructive changes.
   - [ ] Delete source contents, recreate source directory, and extract selected snapshot.

9. CLI and REPL integration
   - [ ] Wire argparse for required `--source` and `--dest`, optional `--ignore`.
   - [ ] Implement fixed menu REPL loop and action dispatch.
   - [ ] Keep boundary exception handling in CLI entrypoint.

10. Scripts and documentation
    - [ ] Add `.command` wrappers for install/run/test/clean.
    - [ ] Write `README.md` with usage, safety notes, ignore semantics, timestamp rules, and restore behavior.
    - [ ] Ensure `revzip` naming remains lowercase in docs and scripts.

11. Verification and test coverage
    - [ ] Unit tests for comment validation/sanitization (including multiline).
    - [ ] Unit tests for path mapping and overlap rejection.
    - [ ] Unit tests for ignore parsing and `re.search` semantics.
    - [ ] Unit tests for archive collision handling (forced same-second case).
    - [ ] Unit tests for duplicate zip-entry detection (mocked inventory).
    - [ ] Unit tests for snapshot discovery warnings + valid-list continuation.
    - [ ] Integration tests for archive/extract roundtrip including empty directories and UTF-8 names.

## Open Questions
- None for MVP scope. Behavior required by this conversation is fully specified.
