# pydeli

A wizard-style Python release helper for publishing one app at a time from a monorepo to TestPyPI and then PyPI.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management, building, and publishing
- A [TestPyPI](https://test.pypi.org/) account
- A [PyPI](https://pypi.org/) account

## Installation

From the monorepo root:

```bash
cd shared/apps/pydeli
uv sync
```

## Usage

```bash
pydeli <app-dir> --archive-dir <archive-dir>
```

- `<app-dir>`: Absolute path (or `~`-prefixed) to the target app directory containing `pyproject.toml`.
- `--archive-dir`: Absolute path (or `~`-prefixed) to the archive root for storing build artifacts.

### Example

```bash
pydeli ~/code/shared/apps/myapp --archive-dir ~/code/secrets/archives/myapp
```

### Using .command Wrappers

Create a `release.command` file for each app:

```bash
#!/bin/bash
cd "$(dirname "$0")"
uv run pydeli ~/code/shared/apps/myapp --archive-dir ~/code/secrets/archives/myapp
```

Make it executable: `chmod +x release.command`

Double-click to run on macOS, or execute from the terminal.

## Workflow

pydeli is a one-shot interactive wizard. On each run it:

1. Validates version consistency across `pyproject.toml`, `__init__.py`, and `__main__.py`
2. Queries TestPyPI and PyPI to verify the version is publishable
3. Offers a choice between **Preflight** (build + archive only) and **Publish** (full release)

### Publish Flow

1. Build artifacts via `uv build`
2. Archive to `<archive-dir>/<version>/`
3. Publish to TestPyPI
4. Verify installation from TestPyPI in an isolated environment
5. Prompt to publish the same build to PyPI

### Preflight Flow

Builds and archives artifacts without publishing. Useful for verifying the build before committing to a release.

## Version Requirements

All version sources must contain the exact same string:

| Source | Location |
|--------|----------|
| `pyproject.toml` | `[project].version` |
| `__init__.py` | `__version__ = "..."` |
| `__main__.py` | `__version__ = "..."` (if present) |

The version must be valid [PEP 440](https://peps.python.org/pep-0440/).

### Version Stage Order

From earliest to latest:

```
dev → alpha (a) → beta (b) → release candidate (rc) → final → post
```

Examples: `0.1.0.dev1` → `0.1.0a1` → `0.1.0b1` → `0.1.0rc1` → `0.1.0` → `0.1.0.post1`

## First-Release Bootstrap

When publishing a project for the first time, pydeli guides you through token setup:

1. **Account-wide token**: Required for first publication (project doesn't exist yet on the registry)
2. **Project-scoped token**: pydeli will prompt you to rotate to a project-scoped token on subsequent runs

Token metadata is stored in `~/Library/Application Support/Pydeli/` (macOS) or the platform-appropriate data directory. Tokens are held in memory during the session and passed via environment variables to `uv publish`.

## Configuration

pydeli requires no configuration files. It reads everything it needs from:

- `pyproject.toml` in the target app directory
- Command-line arguments
- Interactive prompts during the wizard

## Development

```bash
cd shared/apps/pydeli
uv sync
uv run pytest          # run tests
uv run ruff check .    # lint
uv run mypy src/       # type check
```

## License

MIT © nao7sep
