# Review Docs

Validate the current project's user-facing documentation for completeness and accuracy.

## Scope

Check README.md, CLI --help/-h output, REPL /help output, and any other help text or usage guides the app exposes to users. Look for other forms — they may exist beyond the obvious ones.

Skip all other markdown files, plain text, logs, and data files — these are internal reference material.

## Standards

### Coverage

Everything a user needs to install, configure, and use the app must be documented. If a feature exists but isn't documented, that's a finding.

### Accuracy

After multiple rounds of implementation, docs often drift from reality. Verify every claim against the actual source code:
- CLI flags and arguments: do they match the parser definition?
- Configuration options: do they match what the code actually reads?
- Behavior descriptions: do they match what the code actually does?
- Examples: do they actually work?

### Tone and Structure

- README is not a spec document. It must cover: what the app does, how to configure and use it, and what users need to acknowledge (limitations, license, support).
- Leave out implementation details unless they directly affect usage.
- Keep language direct and example-heavy.

## Output

- All good: report inline, no file.
- Minor corrections: report inline and suggest fixing them immediately.
- Non-minor findings: generate a plan at `docs/plans/{YYYY-MM-DD}_{short-description}.md`.
