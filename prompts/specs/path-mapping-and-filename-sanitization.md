# Path Mapping and Filename Sanitization

Specification distilled from a conversation on 2026-02-24 to 2026-02-25.

## Purpose

Define language-agnostic behavior for:
- Mapping user path inputs without any CWD dependence.
- Sanitizing filename segments with `os-safe` mode for cross-platform filesystem validity.
- Sanitizing filename segments with `slugify` mode for semantic, CLI-friendly names.

## Scope

- Path mapping for user-provided strings (`~`, `@`, absolute, relative).
- Filename sanitization for one file or directory name segment at a time.
- Rejection behavior for ambiguous, invalid, or empty results.

## Terms

- App root: distributed application root, not the repository root.
- Base directory: explicitly provided absolute directory used for resolving pure relative paths.
- Filename segment: one file or folder name only, not a full path.
- `os-safe` mode: sanitization targeting Windows-compatible object names.
- `slugify` mode: sanitization targeting readable CLI/search-friendly naming.

## Requirements

### Path Mapping

- Normalize incoming path text from NFD to NFC before mapping checks.
- Reject any input containing NUL (`\0`).
- Never use the current working directory for mapping or resolution.
- Require `app_root` to be absolute.
- Accept absolute paths as-is.
- Map `~` to the user home directory.
- Map `@` to the distributed app root.
- Pure relative paths require an explicit absolute `base_dir`.
- Pure relative paths without `base_dir` must be rejected.
- Reject Windows rooted-but-not-fully-qualified forms such as `\temp` and `C:temp`.
- Resolve dot segments (`.` and `..`) only after mapping onto an explicit absolute context.

### Path Tolerance

- Accept forward and backward slash input styles.
- Accept repeated separators.
- Do not enforce case normalization.
- Preserve Unicode safely (no byte-level truncation/replacement).

### Filename Sanitization: Shared Rules

- Apply sanitization to filename segments only, never to full paths.
- Use explicit mode selection (`os-safe` or `slugify`).
- If sanitization produces an empty result, raise an error (no automatic fallback name).

### `os-safe` Mode (Windows-Strict)

- Treat `< > : " / \ | ? *` and ASCII control characters `0-31` plus `127` as invalid characters.
- Replace invalid characters with a configured replacement token.
- Support a toggle to merge consecutive invalid-character runs into one replacement token.
- Strip trailing periods and trailing Unicode whitespace.
- Check reserved Windows device names using the base name before the first period, case-insensitive: `CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`.
- If matched, prepend a safety prefix (for example `safe_`).

### `slugify` Mode (Semantic/CLI-Friendly)

- Split filename into base name and extension before slugification.
- Lowercase base and extension.
- Preserve Unicode letters, Unicode numbers, `_`, `-`, and `.`.
- Replace all other characters with `-`, including whitespace, punctuation/operators (for example `&`, `?`, `+`, `@`, quotes, brackets), and emojis/symbol-only glyphs.
- Collapse repeated replacement runs to a single `-`.
- Trim leading/trailing hyphens and periods from the base name.
- Reattach the extension after slugification.

## Decision Tables

### Path Mapping Outcomes

| Input condition | Outcome |
|---|---|
| Contains NUL (`\0`) | Reject |
| Starts with `~` | Map to absolute user-home-based path |
| Starts with `@` | Map to absolute app-root-based path |
| Fully absolute path | Accept as-is |
| Pure relative + absolute `base_dir` | Map using `base_dir` |
| Pure relative + no `base_dir` | Reject |
| Windows rooted-not-qualified (`\name`, `C:name`) | Reject |
| Contains `.` or `..` | Resolve only after absolute-context mapping |

### Sanitization Mode Outcomes

| Mode | Primary goal | Invalid/converted set | Empty result |
|---|---|---|---|
| `os-safe` | Filesystem validity across platforms | Windows-forbidden chars + ASCII controls; trailing dot/Unicode whitespace stripped | Error |
| `slugify` | Semantic readable names | Any non-letter/number/`_`/`-`/`.` converted to `-` and collapsed | Error |

## Conformance Examples

- `@/prompts/system.txt` maps to `{app_root}/prompts/system.txt`.
- Relative `../config` with base `/var/app/data` maps first, then resolves to `/var/app/config`.
- `file<:*name` in `os-safe` with merge enabled becomes `file_name`.
- `file<:*name` in `os-safe` with merge disabled becomes `file___name`.
- `test_file` followed by ideographic space and `.` in `os-safe` becomes `test_file`.
- `con.txt` in `os-safe` is prefixed to avoid reserved device-name collision.
- `done & checked.txt` in `slugify` becomes `done-checked.txt`.

## Out of Scope

- Applying filename sanitization to full path strings.
- Inferring `base_dir` from CWD.
- Treating repository root as app root.
- UI/visual-text hardening (for example bidi/RTL control cleanup).
- Automatic fallback placeholders such as `unnamed_file`.

## Open Questions

- Should slugified names also require reserved-device-name handling when used directly as filesystem object names?
- Should post-resolution boundary checks (allowlisted roots) be mandatory in this shared spec?
