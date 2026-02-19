# Developer Playbook

Reference this for deeper context when CLAUDE.md isn't enough.

## Background
20+ years in C#/.NET on Windows, transitioning to Python/TypeScript on Mac. I define WHAT to build; you handle HOW. Suggest the best stack for each project — no predefined technology constraints.

## Language
English for all code, comments, commits, and documentation. Exception: Japanese only for inherently Japanese business domain concepts.

## Architecture Mindset

### Model Structured Data. Always.
Never use raw dicts for structured data. If data has more than one field and lives beyond a single expression, it belongs in a typed model.

```python
# Bad
session["dest_dir"] = "/tmp/out"
result["error_message"] = "File not found"

# Good
@dataclass
class Session:
    dest_dir: Path

@dataclass
class CommandResult:
    error_message: str | None = None
```

Use `dataclass` for simple structured data. Use Pydantic `BaseModel` when you need validation or serialization. Avoid `TypedDict` unless you specifically need dict-compatible typing.

### When to Design Professionally vs. Keep It Simple

**Keep it simple** if the tool is a one-shot script: takes parameters, does work, exits. Even if it collects many pieces of data internally, it's still conceptually simple.

**Design it properly from day one** if the project has any of:
- Persistent state across runs (profiles, settings, history)
- Sessions or a REPL
- Multiple subsystems or providers
- Data that flows through several layers

For these projects, model everything, separate concerns clearly, and resist the urge to "start simple and refactor later." The refactoring cost almost always exceeds the upfront design cost.

### Separate Concerns
- Keep layers distinct: input handling, business logic, data access, output
- Don't mix concerns just to save lines
- A 200-line class that owns one concept is fine. A 50-line class that owns three concepts is not.

### Don't Over-Abstract
- No protocols or interfaces for a single implementation
- Extract when you have 2+ concrete implementations or a genuine cross-cutting concern (auth, logging, retry logic)
- Three similar lines of code are better than a premature abstraction

### Error Handling
Errors propagate via exceptions, caught at system boundaries (CLI entry point, API handler, top-level loop). Never return `None`, `-1`, or other sentinel values to signal failure.

```python
# Bad
def load_config(path: Path) -> Config | None:
    if not path.exists():
        return None  # caller might silently ignore this

# Good
def load_config(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
```

Reserve special return values for non-error outcomes — e.g., returning `None` from a search function when nothing matched is fine, because "not found" is not an error.

## Python Tooling

| Tool | Purpose |
|------|---------|
| uv | Everything: venv, deps, build, publish, Python version management |
| ruff | Linting and formatting |
| mypy | Static type checking |
| pytest | Testing |

uv replaces pip, venv, pipx, pyenv, poetry, and twine. Key commands:

```bash
uv init my-project         # scaffold
uv add requests            # add dependency
uv add --dev pytest ruff   # add dev dependencies
uv build                   # build wheel + sdist
uv publish                 # publish to PyPI
uv tool install my-tool    # install CLI globally (replaces pipx)
uv run my-tool             # run without installing
```

## Project Structure (Python)

```
project-name/
├── src/
│   └── project_name/      # underscore, not dash
│       ├── __init__.py
│       ├── __main__.py
│       └── ...
├── tests/
│   ├── __init__.py
│   └── test_*.py
├── scripts/               # .command files for macOS double-click; plain shell elsewhere
├── docs/
├── pyproject.toml
└── README.md
```

## Abstraction Thresholds

| Situation | Action |
|-----------|--------|
| Single implementation | Just write the class or function |
| 2+ implementations | Use Protocol (Python) or interface (TypeScript) |
| Cross-cutting concern | Separate it (middleware, decorator, dependency) |
| Hard to test | Extract dependencies, use DI |
| File > 500 lines | Consider splitting by responsibility |

## Code Review Priorities
When generating or reviewing code, prioritize in this order:

1. **Security** — injection attacks, auth bypasses, input validation, secrets in code
2. **Correctness** — solves the problem, handles edge cases, proper error propagation, resource cleanup
3. **Maintainability** — no unnecessary cleverness or complexity; easy to understand and change later
4. **Fit** — follows existing patterns in the codebase
5. **Style** — only if genuinely confusing; don't nitpick

## Don't Add Silently
If caching, background jobs, WebSockets, logging beyond basics, monitoring, Docker, CI/CD, or similar infrastructure would meaningfully benefit the current task, mention it — but don't implement it unless asked.
