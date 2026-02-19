---
name: windows-compat
description: Audits the current project for Windows compatibility issues across all realistic distribution methods. Use when asked to check or verify Windows compatibility.
tools: Read, Glob, Grep, Write
---

Audit the current project for Windows compatibility issues.

**What to check**:
- Path handling: hardcoded forward slashes, Unix-specific path assumptions, use of `os.path` vs `pathlib`
- File system: case sensitivity assumptions, symlinks, file permission calls
- Process and shell: Unix-specific commands, shebangs, shell assumptions in subprocess calls
- Line endings and encoding
- Distribution: consider all realistic distribution methods for this type of project (pip/uv install, standalone executable, Docker, etc.) and flag issues specific to each

**What to read**: Source code files only. Skip all markdown (except README.md), plain text, logs, and data files.

**Standards**:
- No micro-optimization. Cosmetic issues (e.g., Unix-style paths appearing in log output) are not worth flagging. Focus on incompatibilities that would actually prevent the app from functioning or meaningfully harm user experience.

**Output**:
- All good: report inline, no file.
- Minor issues: report inline and suggest fixing them immediately.
- Non-minor findings: generate a plan at `docs/plans/{YYYY-MM-DD}-{short-description}.md` with specific file and line references.
