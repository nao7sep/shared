# PLAYBOOK

Developer profile and engineering principles for AI-assisted development.

## Identity

- Name: `Nao`
- Handle: `nao7sep`
- Pronouns: `he/him`
- Location: Japan
- Timezone: JST (UTC+9)
- Email: `nao7sep@gmail.com`
- GitHub: `https://github.com/nao7sep`
- Git commit: `nao7sep <nao7sep@gmail.com>`
- Copyright holder: `nao7sep`
- Default license: MIT

## Background

- Strong background in C, C++, and C#/.NET on Windows. Transitioning to Python and TypeScript on Mac.
- English for all code, comments, commits, and documentation.

## Collaboration

- I define WHAT to build; you handle HOW, including recommending the best stack.
- Bias toward action. Do not ask questions that can be deferred or reasonably decided without my input. Names, locations, and cosmetic details can be decided after the work is done.
- When multiple valid approaches exist, pick the simplest one and proceed. Mention the alternative only if the trade-off is non-obvious.

## Conventions

### Repos

- `~/code/shared/` is a public mono repo of reusable tools and libraries.
- `~/code/secrets/` is a private repo for configurations, credentials, and personal-use utilities.

### Naming

- Directories and files: `kebab-case`
- Plan documents: `{YYYY-MM-DD}_{short-description}.md` in `docs/plans/` within the project directory. Underscores separate semantic groups; hyphens separate words within a group (e.g., `2026-02-20_cli-bookmark-manager.md`).

### Reusable Recipes

AI-agnostic task prompts live in `shared/prompts/recipes/`. These are standalone instructions that can be loaded into any AI (Copilot, Claude, Codex, Gemini) to execute a specific task.

## Engineering

### Data Modeling

Never use raw dicts for structured data. If data has more than one field and lives beyond a single expression, it belongs in a typed model — `dataclass` for simple cases, Pydantic `BaseModel` when validation or serialization is needed.

### Complexity

Keep it simple for one-shot scripts that take input, do work, and exit. Design from day one when there is persistent state, sessions, multiple subsystems, or data flowing across layers.

### Separation of Concerns

Keep layers distinct: input handling, business logic, data access, output. Do not mix concerns only to save lines. A 200-line class with one responsibility is better than a 50-line class with three.

### Abstraction

- Single implementation: concrete class/function.
- Two or more implementations: introduce Protocol/interface.
- Cross-cutting concern: separate middleware/decorator/dependency.
- Hard to test: extract dependencies and use DI.
- File >500 lines: consider split by responsibility.
- Three repeated lines are better than a bad abstraction.

### Error Handling

- Raise exceptions for error paths. Catch at system boundaries (CLI entry point, API handler, top-level loop).
- No sentinel values (`None`, `-1`, magic strings) for errors. Special return values are acceptable only for non-error outcomes (e.g., search miss).
- Every unhandled exception path must surface to the user with a clear message.

### Code Review Priorities

1. Security
2. Correctness
3. Maintainability
4. Fit with existing codebase
5. Style (only when clarity is affected)

## Tooling

### Python

`uv` for package/env management (replaces pip, venv, pipx, pyenv, poetry, twine). `ruff` for linting. `mypy` for type checking. `pytest` for testing.

### TypeScript

`npm` for package management.

## Guardrails

- **TODO.md is managed by `tk`** and synced with a JSON data file. Never edit `TODO.md` directly.
- **Do not add infrastructure silently.** If caching, background jobs, WebSockets, advanced logging, monitoring, Docker, or CI/CD would materially help, mention it first and implement only on request.
