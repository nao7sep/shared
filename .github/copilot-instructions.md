# Developer Context

## Repos
- `~/code/shared/` — public mono repo of reusable tools and libraries
- `~/code/secrets/` — personal configurations, private credentials, and personal-use utilities not intended for public distribution

## Background
20+ years in C#/.NET on Windows, transitioning to Python/TypeScript on Mac. I define WHAT to build; you handle HOW, including suggesting the best stack. No predefined technology constraints.

## Language
English for all code, comments, commits, and documentation. Exception: Japanese only for inherently Japanese business domain concepts.

## Architecture Mindset

**Model structured data. Always.**
Never use raw dicts for structured data — session state, command results, configuration, API responses, etc. Use typed models (dataclasses, Pydantic, or equivalent) so every piece of data has a name, a type, and a clear owner. `session["dest_dir"]` is a code smell; `session.dest_dir` is not.

**Separate concerns from day one** for any project that has persistent state, sessions, profiles, or multiple subsystems. One-shot scripts that take input, do work, and exit can stay simple even if they handle a lot of data.

**Don't over-abstract.** No interfaces or protocols for a single implementation. Extract only when there are 2+ concrete implementations or a genuine cross-cutting concern.

**Raise exceptions on errors.** Errors propagate via exceptions caught at system boundaries. Never return `None`, `-1`, or sentinel values to signal failure. Reserve special return values for non-error outcomes (e.g., "not found" in a search is not an error).

## Python Tooling
- **Package/env management**: uv (replaces pip, venv, pipx, pyenv, poetry — use `uv build` and `uv publish` for PyPI)
- **Linting**: ruff
- **Type checking**: mypy
- **Testing**: pytest
- **CLI tool installation**: `uv tool install` (replaces pipx)

## Don't Edit TODO.md
The `TODO.md` at each repo root is managed by the `tk` task manager, which keeps it in sync with a JSON data file. Editing `TODO.md` directly breaks that sync. Never modify `TODO.md` files.

## Don't Add Silently
If caching, background jobs, WebSockets, logging beyond basics, monitoring, Docker, CI/CD, or similar infrastructure would meaningfully benefit the current task, mention it — but don't implement it unless asked.
