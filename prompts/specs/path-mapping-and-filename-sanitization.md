# Shared Spec: Path Mapping and Filename Sanitization

Specification distilled from conversation on 2026-02-24.

## Purpose

Define cross-platform path mapping and filename sanitization behavior in a language-agnostic way so different AIs can implement the same policy consistently.

## Scope

- Path mapping for user-provided path strings, including `~`, `@`, absolute paths, and relative paths.
- Filename sanitization for individual file or directory name segments.
- Explicit handling and rejection rules for ambiguous or unsafe inputs.

## Terms

- **App root**: the distributed application root, not the repository root where project config files live.
- **Base directory**: an explicitly provided absolute directory used to resolve pure relative paths.
- **Filename segment**: one file or folder name only, not a full path string.

## Requirements

### Core Path Rules

- The current working directory (CWD) must never be used for path resolution.
- App root must be provided as an absolute path.
- Absolute paths are accepted as-is.
- Pure relative paths require an explicitly provided absolute base directory.
- `~` maps to the user home directory.
- `@` maps to the distributed app root.
- Windows rooted-but-not-fully-qualified paths (for example `\temp` or `C:temp`) must be rejected.
- Input containing NUL (`\0`) must be rejected.
- Unicode normalization from NFD to NFC happens before path mapping checks.
- Dot-segment resolution (`.` and `..`) happens only after mapping to an explicit absolute root/base.
- Processing must be Unicode-safe (no byte-level truncation or replacement).

### Path Mapping Decision Matrix

| Input condition | Outcome |
|---|---|
| Contains NUL (`\0`) | Reject |
| Starts with `~` | Convert to absolute path under user home |
| Starts with `@` | Convert to absolute path under app root |
| Fully absolute path | Accept as-is |
| Pure relative path with explicit absolute base directory | Convert to base directory + relative path |
| Pure relative path without base directory | Reject |
| Windows rooted-not-qualified path (`\name`, `C:name`) | Reject |
| Contains `.` or `..` | Resolve only after mapping to explicit absolute context |

### Tolerance Rules

- Accept both slash styles as input where possible.
- Accept repeated separators.
- Do not force case normalization; let filesystem semantics decide.

### Filename Sanitization (Segment Only)

Apply this pipeline to individual file/folder names only, never to full path strings.
The sequence is mandatory.

1. Identify invalid characters:
- Windows forbidden characters: `< > : " / \ | ? *`
- ASCII control characters: code points 0-31 and 127

2. Replace invalid characters with a safe replacement token.
- Support an option to merge consecutive invalid-character runs into a single replacement token.

3. Strip trailing periods and all trailing Unicode whitespace.

4. Handle Windows reserved names:
- Check base name (text before first `.`), case-insensitive, against `CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`.
- If matched, prepend a safety modifier (for example `safe_`) to avoid reserved-name collisions.

5. Apply fallback when the result is empty.
- Use a default placeholder name (for example `unnamed_file`).

## Conformance Examples

- `@/prompts/system.txt` -> `{app_root}/prompts/system.txt` (absolute).
- Relative `../config` with base `/var/app/data` -> map first, then resolve to `/var/app/config`.
- `file<:*name` with merge enabled -> `file_name`; with merge disabled -> `file___name`.
- `test_file` followed by ideographic space + `.` at end -> trailing Unicode whitespace and `.` removed.
- `con.txt` -> prefixed with safety modifier to avoid reserved Windows device name.

## Out of Scope

- Applying filename sanitization to whole path strings.
- UI-focused bidi/RTL cleanup and other visual-text normalization beyond the stated filesystem policy.
- Inferring base directory from CWD.
- Treating repository root as app root for `@`.

## Open Questions

- Should post-resolution boundary checks (for example allowlisted roots) be mandatory in this shared spec or defined per application?
