# revzip

`revzip` is an interactive CLI that archives a source directory into zip snapshots and restores the source directory to a selected snapshot.

Each snapshot writes two files into `--dest`:
- `{timestamp}_{sanitized-comment}.zip`
- `{timestamp}_{sanitized-comment}.json`

## Requirements

- Python `>=3.10`
- `uv` installed

## Install

```bash
cd /path/to/revzip
uv tool install --editable .
```

Or:

```bash
./scripts/install.command
```

## Run

```bash
revzip --source /absolute/source --dest /absolute/dest [--ignore /absolute/ignore.txt]
```

## Startup Path Rules

- `--source` and `--dest` are required.
- `--ignore` is optional.
- Pure relative paths are rejected.
- Accepted forms:
  - absolute paths
  - `~` mapped to home
  - `@` mapped to app root
- CWD is never used for path resolution.
- `--source` and `--dest` must not overlap (same path, ancestor, or descendant).
- `--dest` is created if missing.
- `--dest` must be a directory if it already exists.

## REPL Menu

After startup validation, the app shows only:

1. Archive
2. Extract
3. Exit

## Archive Behavior

- Archive comment is required.
- Comment input accepts multiline text; input ends with an empty line.
- Stored metadata comment:
  - uses `strip()`
  - preserves internal newlines
- Filename comment segment:
  - replaces spaces/newlines and reserved characters `/ \ : * ? " < > |` with `-`
  - merges consecutive replacement runs into one `-`
  - trims leading/trailing `-` after replacement
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
- Invalid metadata JSON or missing corresponding zip are warned loudly and skipped.
- Valid snapshots are sorted by `created_utc` descending.
- Snapshot list rows use left-padded indices and `|` separators.
- Restore requires:
  - numeric selection
  - exact `yes` confirmation
- Zip integrity is verified before destructive restore.
- Restore replaces source contents with the selected snapshot exactly.

## Timestamp Rules

- Internal timestamp field: UTC ISO 8601 with microseconds and `Z` (`created_utc`).
- User-facing timestamp field: local `YYYY-MM-DD HH:MM:SS` (`created_at`).
- UTC fields include `utc` in their names.

## Metadata JSON

Each snapshot metadata file contains:

- `created_utc`
- `created_at`
- `comment`
- `comment_filename_segment`
- `zip_filename`
- `archived_files` (sorted)
- `empty_directories` (sorted)

`archived_files` and `empty_directories` use platform-native path separators.

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
