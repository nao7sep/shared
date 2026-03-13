# emojihunt

Scan directories for emoji usage and generate HTML risk reports.

emojihunt detects emoji characters in source files, classifies them by rendering risk (unpredictable display across editors, fonts, and operating systems), and outputs self-contained HTML reports with sorting and filtering.

## Installation

Requires Python 3.10+.

```sh
cd ~/code/shared/apps/emojihunt
uv sync
```

The `emojihunt` command is then available via `uv run emojihunt`.

## Commands

### `scan` — scan files for emoji usage

```sh
emojihunt scan \
  --target ~/code/shared/apps/myapp/src \
  --target ~/code/shared/apps/myapp/tests \
  --report-dir ~/reports \
  --ignore-file ~/code/shared/apps/myapp/.emojihuntignore
```

| Option | Required | Description |
|---|---|---|
| `--target` | Yes | Directory or file to scan. Repeatable. |
| `--report-dir` | Yes | Directory where output files are written. Must exist. |
| `--ignore-file` | No | File with ignore patterns (one regex per line). |

Produces two files in `--report-dir` with a shared local-time timestamp prefix:

- `YYYY-MM-DD_HH-MM-SS_emojihunt-report.html` — emoji findings with occurrence counts, risk levels, and Unicode metadata.
- `YYYY-MM-DD_HH-MM-SS_emojihunt-paths.txt` — every file path the scanner handled, one per line, sorted alphabetically. Files that could not be read are flagged:
  - `<path> | SKIPPED` — binary file, not scanned for emojis.
  - `<path> | ERROR: <message>` — file could not be read.

### `catalog` — generate a reference catalog

```sh
emojihunt catalog --out-file ~/reports/emoji-catalog.html
```

| Option | Required | Description |
|---|---|---|
| `--out-file` | Yes | Path to the output HTML file. Parent directory must exist. |

Generates an HTML file listing every emoji known to the `emoji` Python package, sorted by code point, with the same risk classification and metadata columns as the scan report.

## Path support

All path arguments (`--target`, `--report-dir`, `--ignore-file`, `--out-file`) support:

- `~` — expands to the user's home directory.
- `@` — expands to the emojihunt package root.
- Absolute paths — used as-is.

Relative paths without `~` or `@` are rejected. The app never depends on the current working directory.

## Ignore patterns

The ignore file contains one regex pattern per line. Blank lines and lines starting with `#` are skipped.

Each pattern is matched (via `re.search`) against the **relative path** from the target root. For example, if the target is `/projects/myapp` and a file exists at `/projects/myapp/dist/bundle.js`, the pattern is matched against `dist/bundle.js`.

Patterns apply to both directories and files. When a directory matches, the scanner skips it entirely without reading its contents.

Example ignore file:

```
# Version control
^\.git/

# Build artifacts
^dist/
^build/
node_modules
__pycache__

# Binary formats
\.(png|jpg|gif|ico|woff2?|ttf|eot|pdf)$
```

## Risk classification

Emojis are classified into three risk levels based on Unicode properties:

**RED** — unpredictable rendering, needs attention:
- Contains a variation selector (`U+FE0E` or `U+FE0F`) — many apps ignore these.
- `Emoji_Presentation=No` — defaults to text rendering; appearance depends on the active font.

**YELLOW** — fragmentation risk, review recommended:
- Contains a Zero Width Joiner (`U+200D`) — may display as separate characters on some platforms.
- Contains a skin tone modifier — may fragment on older systems.
- Emoji version 14.0 or newer — may render as missing-glyph boxes on older operating systems.

**No highlight** — safe. Single-codepoint emoji with color-default presentation and mature Unicode version.

## HTML output

Reports are self-contained HTML files with embedded CSS and JavaScript. No external dependencies — they work fully offline.

Features:
- Click any column header to sort.
- Use the filter input to search across all columns.
- Row background colors indicate risk level (red/yellow).

HTML is formatted with each table cell on its own line for clean `git diff` output.

## Development

```sh
uv run pytest          # run tests
uv run ruff check .    # lint
uv run mypy .          # type check
```

## License

MIT
