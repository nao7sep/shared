# Review Code

Review the current project's source code for bugs, logic errors, security issues, and architectural violations.

## Scope

Read source code files only. Skip markdown (except README.md), plain text, logs, and data files — these are temporary or legacy reference material.

## What To Look For

### Separation of Concerns

- UI, domain logic, commands, and data handling must not be tangled.
- Flag a separation issue only when you can name two distinct responsibilities. Do not report file length as a finding.
- Long files are acceptable when cohesive (parsers, state machines, command registries, generated code).
- Any finding must include concrete evidence (mixed layers in the same function, recurring cross-module edits to ship one change, or tests requiring unrelated setup).
- If recommending a split, specify the proposed boundaries and how behavior and API stability will be protected during migration.

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

## What Not To Look For

- Style issues, naming preferences, or formatting — unless they affect clarity.
- Micro-optimizations with no measurable impact.
- Refactoring opportunities — these belong in a separate refactor-code pass.
- Code you cannot demonstrate to be wrong. Unclear intent is not a finding.

## Existing Files

When the output directory already contains files:

- List filenames and directory structure to avoid naming collisions.
- Do not read the contents of existing files.
- Do not update or overwrite existing files.

## Output

- All good: report inline, no file.
- Minor points that can be fixed quickly: report inline and suggest fixing them immediately.
- Non-minor findings: generate a plan as `{YYYY-MM-DD}_{short-description}.md` in a location relevant to the current app/task context, with specific file references and clear rationale for each finding.
