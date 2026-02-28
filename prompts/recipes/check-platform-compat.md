# Check Platform Compatibility

Audit the current project's source code for cross-platform compatibility issues.

## Scope

Read source code files only. Skip markdown (except README.md), plain text, logs, and data files.

The default stance is that apps should be cross-platform unless there is a clear reason why it is impossible. A hard dependency on a platform-specific module (e.g., a macOS-only framework or a Windows-only COM library) is a valid reason to limit platform scope. Everything else should be made to work everywhere with reasonable effort.

Before starting, determine which platforms are relevant by checking:
- README or docs for stated platform support
- CI configuration for tested platforms
- If neither exists, infer from the project type:
  - Local apps (CLI tools, desktop utilities): macOS is primary; Windows is secondary; Linux is rare but nice to have.
  - Server or remote apps: Linux is primary; Windows (Azure) is secondary; macOS is not a target.
  - If the type is unclear, default to macOS + Windows + Linux in that priority order.

## What To Check

### Path Handling

- Hardcoded path separators (`/` or `\`) instead of `os.path.join`, `pathlib.Path`, or `path.join`.
- Unix-specific path assumptions (`/tmp`, `/home`, `~` expansion without library support).
- Case sensitivity assumptions in file lookups.

### File System

- Symlink usage without fallback for platforms that don't support them or require elevated privileges.
- File permission calls (`chmod`, `os.stat` mode bits) that don't exist or behave differently across platforms.
- File locking mechanisms that are platform-specific.

### Process and Shell

- Shell commands assumed to exist everywhere (`grep`, `sed`, `which`, `cmd.exe`).
- Shebangs that won't work on Windows.
- Subprocess calls that assume a specific shell (`/bin/sh`, `bash`, `cmd`).
- Signal handling (`SIGTERM`, `SIGKILL`) that differs across platforms.

### Conditional Platform Handling

- Modules that behave differently or are unavailable on some platforms (e.g., `readline` on Windows) do not automatically make an app platform-incompatible. Flag these, but recommend conditional loading (e.g., import only when `os.name != "nt"`) rather than dropping platform support.
- Look for opportunities where a platform check or a try/except import could replace a blanket platform restriction.
- Only mark an app as single-platform when it has a hard, non-optional dependency on a platform-specific module with no reasonable workaround.

### Line Endings and Encoding

- Hardcoded `\n` in contexts where the OS line ending matters (writing user-visible files, parsing external input).
- Encoding assumptions (UTF-8 without explicit specification where the platform default might differ).

### Distribution

- Consider all realistic distribution methods for this project type (pip/uv install, npm install, standalone binary, Docker, etc.).
- Flag issues specific to each method on each target platform.

## What Not To Flag

- Cosmetic issues (e.g., Unix-style paths appearing only in log output that users don't act on).
- Platform differences that are handled by a dependency the project already uses.
- Issues in test code that only runs in CI on a known platform.

## Existing Files

When the output directory already contains files:

- List filenames and directory structure to avoid naming collisions.
- Do not read the contents of existing files.
- Do not update or overwrite existing files.

## Output

- All good: report inline, no file.
- Minor issues: report inline and suggest fixing them immediately.
- Non-minor findings: generate a plan as `{YYYY-MM-DD}_{short-description}.md` in a location relevant to the current app/task context, with specific file and line references.
