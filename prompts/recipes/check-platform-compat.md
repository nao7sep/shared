# Check Platform Compatibility

Audit the current project's source code for cross-platform compatibility issues.

## Scope

Read source code files only. Skip markdown (except README.md), plain text, logs, and data files.

Before starting, determine which platforms are relevant by checking:
- README or docs for stated platform support
- CI configuration for tested platforms
- If neither exists, infer from the project type:
  - Local apps (CLI tools, desktop utilities): macOS is primary; Windows support is optional but worth flagging.
  - Server or remote apps: Linux is the target.
  - If the type is unclear, default to macOS + Linux.

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

## Output

- All good: report inline, no file.
- Minor issues: report inline and suggest fixing them immediately.
- Non-minor findings: generate a plan as `{YYYY-MM-DD}_{short-description}.md` in a location relevant to the current app/task context, with specific file and line references.
