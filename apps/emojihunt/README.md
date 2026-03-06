# emojihunt

Scan files and directories for emoji usage and produce HTML artifacts for review.

## Usage

### Generate the full emoji catalog

```
emojihunt catalog --output PATH
```

Writes a complete HTML table of all known emoji sequences, sorted by canonical code point sequence. Each entry includes the rendered emoji, name, code points, Unicode version, presentation default, structural attributes (variation selector, ZWJ, skin tone modifier), risk level, risk reasons, and semantic group.

### Scan for emoji in files

```
emojihunt scan --target PATH [--target PATH ...] --output-dir DIR [--ignore-file FILE]
```

Scans one or more files or directories. Writes a timestamped HTML findings report aggregated by unique emoji sequence with occurrence counts. Entries are ordered: red first, yellow second, then unhighlighted; within each group, higher occurrence counts first.

## Risk model

| Condition | Level |
|---|---|
| Variation selector present | Red |
| Text-default or ambiguous presentation | Red |
| Zero width joiner present | Yellow |
| Skin tone modifier present | Yellow |
| Unicode 14.0 or later | Yellow |

Red wins when both red and yellow conditions are triggered. All triggered reasons are listed.

## Ignore file

Pass a file of Python regex patterns via `--ignore-file`. Each non-empty, non-comment line is a pattern matched via `re.search()` against the full absolute path of each file or directory. Directories are checked before entering; files are checked before scanning. Lines starting with `#` are comments.

Example patterns:

```
# Skip virtual environments
/\.venv/

# Skip minified assets
\.min\.js$
```

## Path rules

- Absolute paths and `~`-prefixed paths are accepted.
- `@`-prefixed paths resolve relative to the installed package directory.
- Pure relative paths are rejected.
- Paths are normalized from NFD to NFC. Paths containing NUL are rejected.

## Scripts

| Script | Location | Purpose |
|---|---|---|
| `run.command` | `secrets/apps/emojihunt/scripts/` | Scan `~/code` with personal ignore list |
| `install.command` | `shared/apps/emojihunt/scripts/` | `uv sync` |
| `test.command` | `shared/apps/emojihunt/scripts/` | Run pytest |
| `clean.command` | `shared/apps/emojihunt/scripts/` | Remove build and cache artifacts |

## Development

```
uv sync
uv run emojihunt --help
uv run pytest tests/ -v
uv run ruff check .
uv run mypy src/
```
