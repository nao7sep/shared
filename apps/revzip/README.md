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

`.command` files are zsh convenience wrappers (for example on macOS).
On other platforms, run the equivalent `uv` commands directly.

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

After startup validation, the app prints:

- app banner
- loaded parameter block (source, destination, ignore file, ignore pattern count)

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
  - `Scanned: X dirs | Y files`
- During archive, one in-place line is updated after each archived file:
  - `Archived: X / Y files`
- Ignored paths are not counted in those progress counters.
- Created archive output line uses:
  - `Created ZIP: ...`

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
- Snapshot list rows show index, timestamp, and comment using `|` separators.
- Snapshot list block is visually isolated with one empty line above and below rows.
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
