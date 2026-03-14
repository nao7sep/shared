# revzip

`revzip` is an interactive CLI that archives a source directory into zip snapshots and restores the source directory to a selected snapshot.

Each snapshot writes two files into `--dest`:
- `{timestamp}_{sanitized-comment}.zip`
- `{timestamp}_{sanitized-comment}.json`

## Requirements

- Python `>=3.10`
- `uv` installed

## Setup

```bash
cd /path/to/shared/apps/revzip
uv sync
```

## Run

```bash
uv run revzip --source /absolute/source --dest /absolute/dest [--ignore /absolute/ignore.txt]
```

## Startup Path Rules

- `--source` and `--dest` are required.
- `--ignore` is optional.
- Pure relative paths are rejected.
- Accepted forms:
  - absolute paths
  - `~` mapped to home
  - `@` mapped to the `revzip` package directory used by the app
- `@` does not mean repository root.
- CWD is never used for path resolution.
- `--source` must already exist.
- `--source` must be a directory.
- `--source` and `--dest` must not overlap (same path, ancestor, or descendant).
- `--dest` is created if missing.
- `--dest` must be a directory if it already exists.
- `--ignore` must point to an existing file if provided.

## REPL Menu

After startup validation, the app prints:

- app banner
- loaded parameter block (source, destination, ignore file, ignore pattern count)
- each later output segment owns its leading empty line; no segment emits a trailing empty line

Then it shows only this REPL menu:

1. Archive
2. Extract
3. Exit

## Archive Behavior

- Archive comment is required.
- Comment input is a single prompt line.
- Stored metadata comment:
  - uses `strip()`
  - preserves trimmed input text
- Filename comment segment:
  - slugifies base and extension separately
  - lowercases both base and extension
  - preserves Unicode letters, Unicode numbers, `_`, `-`, and `.`
  - replaces all other characters (including whitespace, punctuation, `+`, `@`, emojis) with `-`
  - merges every consecutive hyphen run into one `-`
  - trims leading/trailing `-` and `.` from the base name
  - reattaches the extension after slugification
  - fails archive if sanitized segment becomes empty
- Snapshot filename format:
  - `YYYY-MM-DD_HH-MM-SS_comment-segment.zip` (local time)
- Metadata filename uses same base with `.json`.
- If the target `.zip` or `.json` already exists, archive fails with collision error.
- Built-in ignores:
  - `.git`
  - `.DS_Store`
  - `Thumbs.db`
  - `desktop.ini`
- Symlinks are skipped with warnings.
- Archive includes:
  - regular files
  - empty directories
- Zip entry names are source-relative and never include the source directory name.
- If nothing matches (no files and no empty directories), no snapshot is created.
- During scan, one in-place line is updated after each scanned directory:
  - `Scanned: 1,234 dirs | 5,678 files` (counts use thousands separators)
- During archive, one in-place line is updated after each archived file:
  - `Archived: 1,234 / 5,678 files` (counts use thousands separators)
- Ignored paths are not counted in those progress counters.
- After archive completes, three output lines are printed:
  - `Archived X file(s) and Y empty directory(s).`
  - `Created ZIP: <filename>.zip`
  - `Created metadata: <filename>.json`

## Ignore File Semantics

- One regex per line.
- Each line is trimmed.
- Empty lines are ignored.
- Lines beginning with `#` are ignored.
- Matching uses `re.search` (partial match).
- No automatic `^` / `$` is added.
- Match target string is:
  - `raw_source_argument + "/" + relative_path`
- If a directory path matches ignore rules, that subtree is pruned and treated as non-existent.

## Extract Behavior

- Snapshot candidates are discovered from metadata JSON files in destination.
- Invalid metadata JSON is warned loudly and skipped.
- Metadata is warned and skipped if:
  - the corresponding zip is missing
  - `zip_filename` does not match the sibling `.zip` filename
  - `created_utc` or `created_at` is invalid
- Snapshot list rows show index, timestamp, and comment using `|` separators.
- Restore requires:
  - numeric selection
  - exact `yes` confirmation
- Zip integrity is verified before destructive restore.
- Restore extracts into a staging directory before replacing `--source`.
- If zip verification or extraction fails, the existing source directory is left unchanged.
- Restore replaces source contents with the selected snapshot exactly.

## Metadata JSON

Each snapshot metadata file contains:

- `created_utc`: UTC ISO 8601 with microseconds and `Z`
- `created_at`: local `YYYY-MM-DD HH:MM:SS`
- `comment`
- `comment_filename_segment`
- `zip_filename`
- `archived_files`
- `empty_directories`

`archived_files` and `empty_directories` use platform-native path separators.
UTC metadata fields include `utc` in their names.

## Development

Run tests:

```bash
uv sync --group dev
uv run pytest tests/ -v
```

Or:

```bash
./scripts/test.command
```
