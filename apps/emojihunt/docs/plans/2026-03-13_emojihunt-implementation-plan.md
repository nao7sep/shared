# emojihunt

Implementation plan generated from conversation on 2026-03-06, refined on 2026-03-13.

## Overview

emojihunt is a Python CLI tool that scans directories and files for emoji usage and generates HTML reports with risk classification. It also generates a standalone catalog of all emojis known to the Python ecosystem. The tool helps developers find "dangerous" emojis — characters whose visual rendering varies unpredictably across editors, fonts, and operating systems — and assess their risk level at a glance.

The app produces self-contained HTML files with embedded CSS and offline-capable JavaScript for sorting and filtering. HTML output uses multi-line formatting so that git diffs isolate changes to individual table cells.

## Requirements

### General

- App name is `emojihunt`, always all lowercase.
- App lives at `~/code/shared/apps/emojihunt/`.
- Python, managed with `uv`. Entry point defined in `pyproject.toml` under `[project.scripts]` so users invoke `emojihunt` directly.
- Linting with `ruff`, type checking with `mypy`, testing with `pytest`.
- MIT license, copyright holder `nao7sep`.
- Never depend on the current working directory for any path resolution or default behavior.
- Support `~` (user home) and `@` (app root) in all user-provided paths, per the path mapping spec. Accept both forward and backward slashes. Reject pure relative paths that lack an explicit base directory context.
- Platform compatible (macOS, Linux, Windows).

### CLI Interface

- Use Typer with two subcommands: `catalog` and `scan`. These are mutually exclusive by design (Typer subcommands).
- Running `emojihunt` with no subcommand prints help.

#### `catalog` subcommand

```
emojihunt catalog --out-file <path>
```

- `--out-file`: required. Path to the output HTML file. Supports `~` and `@`.
- Generates a reference HTML file listing every emoji known to the upstream Python packages, with full metadata and risk classification.
- No directory scanning occurs in this mode.

#### `scan` subcommand

```
emojihunt scan --target <path> [--target <path> ...] --report-dir <path> [--ignore-file <path>]
```

- `--target`: required, repeatable. Paths to directories or individual files to scan. Supports `~` and `@`. At least one must be provided; omitting all targets is an error.
- `--report-dir`: required. Directory where the report HTML and handled-path list will be written. Supports `~` and `@`.
- `--ignore-file`: optional. Path to a file containing regex patterns for paths to ignore. Supports `~` and `@`.

### Ignore System

- The ignore file contains one regex pattern per line.
- Blank lines and lines starting with `#` are ignored (comments).
- Each pattern is matched against the relative path from the corresponding target root. For example, if `--target /projects/alpha` is specified and the app encounters `/projects/alpha/dist/bundle.js`, the relative path tested is `dist/bundle.js`.
- Patterns apply to both directory paths and file paths. When the app encounters a directory entry, it checks the directory's relative path against the patterns before entering. If the directory matches, the app skips it entirely — no descent, no I/O.
- There are no built-in default ignore patterns. The user controls all filtering via the ignore file. Without an ignore file, the app scans everything, including `.git` directories.
- Patterns are compiled as Python `re` regular expressions. A pattern that fails to compile causes an immediate error with the line number and pattern text.

### Directory Traversal

- Use `os.scandir()` for lazy, incremental directory traversal — equivalent to .NET's `DirectoryInfo`. The app enters one directory at a time and inspects each entry before deciding whether to recurse.
- For each directory entry:
  1. If it is a directory: check its relative path against ignore patterns. If ignored, skip entirely. Otherwise, recurse into it.
  2. If it is a file: check its relative path against ignore patterns. If ignored, skip. Otherwise, attempt to read it.
- The app never calls a method that retrieves all file paths in a directory tree at once.

### File Reading

- Read each file line by line. Emojis do not split across lines, so line-by-line reading is sufficient and enables future line-number tracking.
- Attempt to open files as UTF-8 text.
- If a file cannot be decoded (binary file): skip it, print a warning to the terminal, and log the path in the handled-path list with a `| SKIPPED` flag.
- If a file encounters a read error (permission denied, I/O error, partial decode failure): skip it, print a warning to the terminal, and log the path with `| ERROR: <short message>`.
- Successfully read files are logged in the handled-path list with no flag.

### Emoji Detection

- Use Python packages for emoji detection and Unicode property lookup. Do not download or bundle raw Unicode data files. Rely on packages maintained by teams so that updating the dependency automatically brings the latest Unicode data.
- Candidate packages: `emoji` (for emoji recognition and name lookup), Python's built-in `unicodedata` (for Unicode property queries), and optionally the `regex` package (for `\p{Emoji}` pattern support). Choose the combination that reliably provides:
  - Emoji identification (including multi-code-point sequences)
  - `Emoji_Presentation` property (Yes/No)
  - Variation selector detection (`U+FE0E`, `U+FE0F`)
  - Zero Width Joiner detection (`U+200D`)
  - Skin tone modifier detection
  - Unicode version in which the emoji was introduced
  - Official Unicode name / CLDR name
- Parse each line to extract complete emoji sequences (including ZWJ sequences, variation selectors, and skin tone modifiers as single logical units).

### Risk Classification

Every emoji is classified into one of three risk levels. Classification is assessed in this order — the first matching rule wins:

#### RED (immediate action — unpredictable rendering)

Row background: `#fee2e2` (light red).

An emoji is RED if any of the following is true:

1. It contains a Variation Selector: `U+FE0E` (text presentation) or `U+FE0F` (emoji presentation). Many apps and fonts ignore these selectors, causing inconsistent rendering.
2. Its `Emoji_Presentation` property is `No` (defaults to text rendering). Characters like the checkmark (`U+2714`) and lightning bolt (`U+26A1`) fall here — their appearance depends entirely on the active font.

#### YELLOW (caution — fragmentation risk)

Row background: `#fef3c7` (light yellow).

An emoji is YELLOW if any of the following is true:

1. It contains a Zero Width Joiner (`U+200D`). Compound emojis (families, professions) can fragment into separate characters on unsupported platforms.
2. It contains a skin tone modifier. Unsupported systems render these as a base emoji plus a colored square.
3. It was introduced in Unicode 14.0 (2021) or later. These are likely to render as missing-glyph boxes on older operating systems.

#### Safe (no highlight)

No background color.

An emoji is safe if it does not trigger any RED or YELLOW condition.

### Output: Scan Report HTML

Generated in `--report-dir` with filename `{YYYY-MM-DD}_{HH-MM-SS}_emojihunt-report.html` using local time.

#### Metadata section

The report begins with a metadata block containing (in a logical order):

- Report title
- Generation timestamp in UTC (internal/roundtrip format per timestamp spec)
- Generation timestamp in local time (human-readable, no timezone label per timestamp spec)
- Scan duration
- Target paths scanned
- Ignore file used (or "None")
- Total files handled (with breakdown: scanned, skipped, errored)
- Total unique emojis found
- Total emoji occurrences

#### Findings table

- Shows only emojis that were actually found in the scanned files.
- Columns (in logical order): Rendered Emoji, Risk Level, Risk Reasons, Name, Code Points, Unicode Version, `Emoji_Presentation`, Is ZWJ Sequence, Occurrence Count.
- Row background color corresponds to risk level.
- Default sort: by occurrence count descending, then by code points ascending.
- JavaScript enables the user to re-sort by clicking column headers.
- JavaScript provides a text filter input that filters rows as the user types. Filtering matches against all text columns.

#### HTML formatting

- Multi-line: each `<tr>` and its `<td>` elements are written on separate, indented lines so that git diffs show exactly which cell changed.
- Self-contained: all CSS is embedded in a `<style>` block. All JavaScript is embedded in a `<script>` block. No external dependencies.
- Clean, simple styling: readable font, simple table borders, adequate spacing. No external fonts or icon libraries.

### Output: Handled-Path List

Generated alongside the scan report in `--report-dir` with filename `{YYYY-MM-DD}_{HH-MM-SS}_emojihunt-paths.txt` using local time (same timestamp as the companion report).

- Plain text file. One line per file path. No header, no metadata, no preamble.
- Contains the full absolute path for every file the app encountered (not directories).
- Sorted alphabetically.
- Files that were successfully scanned: path only (no flag).
- Files that were skipped (binary): `<path> | SKIPPED`
- Files that encountered errors: `<path> | ERROR: <short message>`
- The `|` delimiter ensures paths remain left-aligned for easy visual scanning.

### Output: Catalog HTML

Generated at the path specified by `--out-file` in catalog mode.

#### Metadata section

- Catalog title
- Generation timestamp (UTC and local, same conventions as the scan report)
- Python `emoji` package version (or whichever package provides the data)
- Total emojis in catalog

#### Table

- Shows every emoji known to the upstream Python packages.
- Columns (in logical order): Rendered Emoji, Risk Level, Risk Reasons, Name, Code Points, Unicode Version, `Emoji_Presentation`, Is ZWJ Sequence, Contains Variation Selector, Contains Skin Tone Modifier.
- The catalog is more detailed than the scan report because its purpose is reference and discovery.
- Row background color corresponds to risk level.
- Default sort: ascending by code points.
- JavaScript enables column-header sorting and text filtering (same behavior as the scan report).
- Same HTML formatting rules as the scan report (multi-line, self-contained, clean CSS).

### Console Output

Follow the CLI output formatting spec:

- Every segment emits exactly one leading empty line, except the first segment which emits none.
- No trailing empty lines from any segment.
- Use the segment catalog: Banner (app name/version at startup), Result (operation outcome), Warning (skipped/errored files), Error (fatal errors), Progress (scan progress), Farewell (exit message).
- Plain text by default. No colors or decorations unless explicitly added later.
- Key-value blocks (e.g., summary stats) must align values to the same column.
- Do not hard-wrap output.
- Print explicit empty-state feedback when applicable (e.g., "No emojis found.").

### Timestamp Conventions

Per the shared timestamp spec:

- Internal timestamps (in HTML metadata, in data models): UTC, high precision, roundtrip-safe format with explicit `Z` marker. Variable/key names include `utc`.
- User-facing timestamps (displayed in HTML to the reader): local time, human-readable, no timezone label.
- Filenames: local time, `YYYY-MM-DD_HH-MM-SS` format with underscores between semantic groups.

### Constants and Named Values

Per the shared constants spec:

- Extract literals into named constants when duplicated, non-obvious, contract values, or tunable policy (e.g., `UNICODE_VERSION_THRESHOLD = 14.0`, risk-level color hex codes, CSS class names used across modules).
- Keep self-documenting single-use values inline.
- Constants live in the module that owns the concept. A shared constants module is justified only for values that genuinely cross layer boundaries.
- Use `UPPER_SNAKE_CASE`. Include units in names when the type alone does not convey them.

### Data Modeling

Per the playbook:

- No raw dicts for structured data. Use `dataclass` for models. Use Pydantic `BaseModel` only if validation or serialization is needed (unlikely for this app).
- All structured data with more than one field that lives beyond a single expression gets a typed model.

### Error Handling

Per the playbook:

- Raise exceptions for error paths. Catch at the CLI entry point (Typer command functions) and show clear, user-facing messages.
- No sentinel values for errors.
- Invalid ignore patterns: immediate error with line number and pattern text.
- Missing or inaccessible target paths: immediate error.
- Missing report directory: immediate error (do not auto-create).
- File read failures during scan: warn and continue (non-fatal). Log in handled-path list.

## Architecture

### Layer Separation

Four layers with strict separation of concerns:

```
Input (CLI)  -->  Domain (Scanner, Filter, Analyzer)  -->  Output (Reporter)
                         |
                    Data (Models)
```

- **Input layer** (`cli.py`): Typer command definitions, argument parsing, path resolution (~ and @ mapping), top-level error handling. Knows nothing about emojis or HTML.
- **Data layer** (`models.py`): Dataclasses representing emoji metadata, scan findings, and scan context. Pure data containers with no I/O or business logic.
- **Domain layer**: Three engines, each with a single responsibility:
  - `filter.py`: Compiles regex patterns from the ignore file. Exposes a method to test whether a relative path should be ignored. Knows nothing about scanning or emojis.
  - `scanner.py`: Uses `os.scandir()` for lazy directory traversal. Consults the filter before entering directories. Yields file paths (or handled-path records) to the caller. Knows nothing about emojis or HTML.
  - `analyzer.py`: Wraps upstream Python packages for emoji detection. Given text (a line), extracts emoji sequences and classifies their risk. Knows nothing about files or directories.
- **Output layer** (`reporter.py`): Generates HTML files (catalog and scan report) and the handled-path text file. Takes data models as input. Knows nothing about scanning or emoji detection logic.

### Data Flow: `scan` subcommand

1. CLI parses arguments, resolves paths, loads ignore file (if provided), validates inputs.
2. CLI constructs a `PathFilter` from the ignore patterns.
3. CLI constructs a `DirectoryScanner` with the targets and filter.
4. CLI constructs an `EmojiAnalyzer`.
5. For each file yielded by the scanner:
   - Read line by line.
   - Pass each line to the analyzer to extract emoji findings.
   - Accumulate occurrence counts per unique emoji.
   - Record the file path as a handled path (with status).
6. After scanning completes, pass the aggregated findings and handled paths to the reporter.
7. Reporter writes the scan report HTML and handled-path list to the report directory.

### Data Flow: `catalog` subcommand

1. CLI parses arguments, resolves the output path, validates inputs.
2. CLI constructs an `EmojiAnalyzer`.
3. Analyzer enumerates all known emojis from the upstream package and classifies each.
4. CLI passes the full emoji list to the reporter.
5. Reporter writes the catalog HTML to the specified file.

### Key Dependencies

| Purpose | Package |
|---|---|
| CLI framework | `typer` |
| Emoji detection and names | `emoji` (and/or `regex` for `\p{Emoji}`) |
| Unicode properties | `unicodedata` (stdlib) |
| Path mapping (~ and @) | Custom logic per path mapping spec |
| Ignore pattern matching | `re` (stdlib) |
| HTML generation | String formatting or `jinja2` (decide during implementation) |

### Module Layout

```
src/emojihunt/
    __init__.py
    __main__.py        # entry point: invokes cli
    cli.py             # Input layer: Typer app, subcommands
    models.py          # Data layer: dataclasses
    filter.py          # Domain: ignore-pattern compilation and matching
    scanner.py         # Domain: os.scandir traversal
    analyzer.py        # Domain: emoji detection and risk classification
    reporter.py        # Output layer: HTML and text file generation
```

## Implementation Steps

1. **Project scaffold.** Initialize the project with `uv init`, set up `pyproject.toml` with metadata (name, author, license, entry point), add dependencies (`typer`, `emoji`), configure `ruff` and `mypy`.

2. **Data models.** Define dataclasses in `models.py`: `EmojiMetadata` (char, code points, name, unicode version, risk level, risk reasons, emoji presentation, is ZWJ, has variation selector, has skin tone modifier), `ScanFinding` (wraps `EmojiMetadata` + occurrence count), `HandledPath` (path + status enum + optional error message), `ScanContext` (targets, ignore file path, timestamps, file counts). Define risk level as an enum (RED, YELLOW, SAFE).

3. **Path resolution utility.** Implement `~` and `@` mapping per the path mapping spec. Reject pure relative paths without a base directory. Accept both slash styles. Normalize NFD to NFC. This is used by the CLI layer for all user-provided paths.

4. **Ignore filter.** Implement `filter.py`: load an ignore file, skip blank lines and `#` comments, compile each line as a regex (error on invalid pattern with line number), expose a `is_ignored(relative_path: str) -> bool` method that tests against all patterns.

5. **Directory scanner.** Implement `scanner.py`: accept a list of target paths and a `PathFilter`. For each target, use `os.scandir()` recursively. For each directory entry, compute the relative path from the target root. Check directories against the filter before entering. For files, check against the filter, then attempt to open as UTF-8 text. Yield `HandledPath` records and file content (or a readable file handle). Handle binary detection and read errors gracefully.

6. **Emoji analyzer.** Implement `analyzer.py`: wrap the `emoji` package and `unicodedata` to detect emoji sequences in a line of text. For each detected emoji, extract all metadata fields (name, code points, unicode version, presentation, ZWJ, variation selector, skin tone). Classify risk per the RED/YELLOW/safe rules. Expose a method to enumerate all known emojis for catalog generation.

7. **HTML reporter.** Implement `reporter.py`: generate self-contained HTML files with embedded CSS and JavaScript. Write multi-line HTML (each `<td>` on its own line). Implement metadata sections, risk-level row backgrounds, column-header sorting, and text filtering. Generate the handled-path plain text file. Ensure all JavaScript works on offline HTML files (no CDN, no external resources).

8. **CLI layer.** Implement `cli.py`: define `catalog` and `scan` subcommands with Typer. Parse and resolve all paths. Validate inputs (missing targets, missing report dir, conflicting options). Orchestrate the data flow: construct filter, scanner, analyzer, and reporter. Catch exceptions at the top level and print user-facing error messages. Follow CLI output formatting spec for all console output (banner, progress, warnings, results, farewell).

9. **Console output compliance.** Review all terminal output for conformance with the CLI output formatting spec: single leading blank lines between segments, no trailing blanks, key-value alignment, explicit empty-state feedback, plain text only.

10. **Testing.** Write tests for each layer independently: filter pattern matching, scanner traversal with mock directories, analyzer emoji detection and risk classification, reporter HTML structure. Integration test: end-to-end scan of a test directory with known emoji content.

## Open Questions

- **Emoji package coverage**: The `emoji` Python package may not expose all Unicode properties needed (e.g., `Emoji_Presentation`). If it falls short, the `regex` package with `\p{Emoji_Presentation}` or manual lookup in `unicodedata` may be needed. This will be resolved during implementation of `analyzer.py`.
- **Catalog size and performance**: The full emoji catalog may contain thousands of entries. Whether the generated HTML file size and JavaScript sorting performance are acceptable will be validated during implementation.
- **HTML template approach**: Whether to use raw string formatting or `jinja2` for HTML generation. `jinja2` adds a dependency but improves readability for complex templates. Decision deferred to implementation.
- **`@` (app root) definition**: The path mapping spec defines `@` as the distributed application root. For emojihunt, this is `~/code/shared/apps/emojihunt/`. Whether this is useful in practice (e.g., `--ignore-file @/config/ignore-patterns.txt`) will become clear during use.
- **Future enhancements**: Line-number tracking in findings (the line-by-line reading strategy supports this), REPL mode for interactive exploration, alternative output formats. These are out of scope for the initial implementation.
