# Review Code

Review the current project's source code for bugs, logic errors, security issues, and architectural violations.

## Scope

Read source code files only. Skip markdown (except README.md), plain text, logs, and data files — these are temporary or legacy reference material.

## What To Look For

### Correctness

- Logic errors, off-by-one mistakes, race conditions, unintended mutation.
- Null/None handling: variables assumed non-null without verification.
- Type mismatches or implicit conversions that could fail at runtime.

### Error Handling

- Exceptions must propagate and be caught at system boundaries (CLI entry point, top-level loop, API handler).
- No silent failures: every unhandled exception path must surface to the user with a clear message.
- No sentinel values (`None`, `-1`, magic strings) used to represent errors. Raise exceptions instead.
- Catch-all handlers at boundaries are acceptable for rare edge cases. Common errors must be precisely distinguished and reported.

### Security

- User input must be validated/sanitized before use (SQL queries, shell commands, file paths, URLs).
- Credentials, tokens, and secrets must not appear in source code or logs.
- File operations must not follow user-controlled paths outside intended directories.

### Separation of Concerns

- UI, domain logic, commands, and data handling must not be tangled.
- A reasonable signal: if source files are consistently 5–25 KB, the structure is likely healthy.
- Files over 500 lines should be reviewed for mixed responsibilities.
- 500+ lines alone is not a finding; report only when there is concrete evidence of mixed responsibilities.
- Long files can be acceptable when cohesive (for example: generated code, command registries, parsers, or state machines).
- If recommending a split, specify proposed boundaries and how behavior/API stability will be protected during migration.

## What Not To Look For

- Style issues, naming preferences, or formatting — unless they affect clarity.
- Micro-optimizations with no measurable impact.
- Refactoring opportunities — these belong in a separate refactor-code pass.

## Output

- All good: report inline, no file.
- Minor points that can be fixed quickly: report inline and suggest fixing them immediately.
- Non-minor findings: generate a plan as `{YYYY-MM-DD}_{short-description}.md` in a location relevant to the current app/task context, with specific file references and clear rationale for each finding.
