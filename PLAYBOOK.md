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
- Use these values for project/package metadata by default (for example `pyproject.toml`) unless explicitly told otherwise.

## Background

- Strong background in C, C++, and C#/.NET on Windows. Transitioning to Python and TypeScript on Mac.
- English for all code, comments, commits, and documentation.

## Collaboration

- I define WHAT to build; you handle HOW, including recommending the best stack.
- Bias toward action. Do not ask questions that can be deferred or reasonably decided without my input.
- If the choice is low-risk and reversible, pick the simplest option and proceed.
- If the choice changes architecture or operations (caching, background jobs, WebSockets, advanced logging, monitoring, Docker, CI/CD), propose first and implement only on request.
- Mention alternatives only when the trade-off is non-obvious.

## Conventions

### Repos

- `~/code/shared/` contains reusable, publishable code and docs. Assume contents may become public.
- `~/code/secrets/` contains private configs, credentials, and personal-use utilities. Treat contents as non-public and never copy sensitive data into `shared`.

### Naming

- Directories and files: `kebab-case`
- Generated documents (plans, reviews, analyses): `{YYYY-MM-DD}_{short-description}.md` saved in the directory most relevant to the context. Underscores separate semantic groups; hyphens separate words within a group (e.g., `2026-02-20_cli-bookmark-manager.md`).

### Reusable Recipes

AI-agnostic task prompts live in `shared/prompts/recipes/`. These are standalone instructions that can be loaded into any AI (Copilot, Claude, Codex, Gemini) to execute a specific task.

## Engineering

### Data Modeling

Never use raw dicts for structured data. If data has more than one field and lives beyond a single expression, it belongs in a typed model - `dataclass` for simple cases, Pydantic `BaseModel` when validation or serialization is needed.

### Design Rules

- One-shot scripts: optimize for directness and clarity.
- Systems with persistent state, sessions, multiple subsystems, or cross-layer data flow: define boundaries early.
- Separation of concerns is the highest priority for code structure.
- Keep layers strictly distinct: input handling, business logic, data access, output.
- Reject tangled designs that mix responsibilities just to reduce line count.
- Start concrete. Introduce Protocol/interface when there are two or more implementations.
- Extract dependencies when code is hard to test.
- Split only when you can name two distinct responsibilities with independent reasons to change. File size and function length are never valid reasons to split.
- Large files are acceptable when cohesive. Parsers, state machines, registries, and generated code are typically cohesive regardless of size.
- When splitting, preserve behavior first: keep tests green, keep public APIs stable, and never dump code into generic `utils` modules.
- Prefer small duplication over poor abstraction.

### Error Handling

- Raise exceptions for error paths. Catch at system boundaries (CLI entry point, API handler, top-level loop) and show a clear user-facing message.
- No sentinel values (`None`, `-1`, magic strings) for errors. Special return values are acceptable only for non-error outcomes (e.g., search miss).

### Code Review Priorities

1. Separation of concerns and maintainability
2. Correctness
3. Security
4. Fit with existing codebase
5. Style (only when clarity is affected)

## Pragmatism

- Well-separated concerns and passing tests are the primary release signal. Do not block shipping on hypothetical improvements.
- Do not fix what you cannot demonstrate to be wrong. Unclear code is not broken code.
- Real bugs come from real users. Compensable damage is preferable to over-engineered prevention that delays release.

## Tooling

### Python

- `uv` for dependency and environment management.
- `ruff` for linting.
- `mypy` for type checking.
- `pytest` for testing.

### TypeScript

- `pnpm` for new projects (preferred: strict dependency resolution, fast, disk-efficient — the Node.js equivalent of `uv`).
- `npm` when working on existing projects that already use it.
- `eslint` (with `@typescript-eslint`) for linting.
- `tsc` for type checking.
- `vitest` for testing (preferred: fast, native TypeScript support, Jest-compatible API); `jest` as an alternative for projects with an existing Jest ecosystem.

## Guardrails

- **Git: read-only only.** AI may run git commands that inspect the repo (log, diff, status, show, blame, etc.) but must never run commands that create, modify, or delete commits, branches, tags, or remote state. Those operations are my responsibility.
- **TODO.md is managed by `tk`** and synced with a JSON data file. Never edit `TODO.md` directly.
