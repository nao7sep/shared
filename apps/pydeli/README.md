# pydeli

A Python package release helper. Walks you through building, archiving, and publishing Python packages to TestPyPI or PyPI with interactive guidance.

## Why

- **No GitHub Actions.** Designed for developers who prefer local, manual publication over CI/CD pipelines.
- **Monorepo-friendly.** No Git tags. Works with any directory containing a `pyproject.toml`.
- **Learn by doing.** Guides you through token creation, version validation, and test installation step by step.
- **Local archives.** Keeps a copy of every published artifact for quick bug reproduction.

## Install

pydeli lives in the monorepo. Invoke it with `uv run`:

```bash
uv run --directory ~/code/shared/apps/pydeli pydeli [options]
```

## Usage

### Quick start

Run with no arguments for fully interactive mode:

```bash
uv run pydeli
```

pydeli will prompt for everything: target registry, run mode, app directory, and archive directory.

### CLI options

```
pydeli [APP_DIR] [--archive-dir DIR] [--target testpypi|pypi] [--dry-run | --wet-run]
```

All options are optional. If omitted, pydeli asks interactively.

| Option | Description |
|---|---|
| `APP_DIR` | Path to the app directory to publish. Supports `~` and absolute paths. |
| `--archive-dir DIR` | Root directory for archived build artifacts. |
| `--target testpypi\|pypi` | Target registry. |
| `--dry-run` | Build and archive only. No upload, no test-install. |
| `--wet-run` | Build, archive, and upload. |

### Using .command files (macOS)

Create a `.command` file in each app for double-click releases:

```bash
#!/usr/bin/env bash
uv run --directory ~/code/shared/apps/pydeli pydeli \
  --archive-dir ~/code/shared/releases
```

This pre-fills the archive directory. pydeli will interactively ask for the target registry, run mode, and app directory.

A more complete version:

```bash
#!/usr/bin/env bash
uv run --directory ~/code/shared/apps/pydeli pydeli \
  ~/code/shared/apps/my-app \
  --archive-dir ~/code/shared/releases
```

## Workflow

Each run targets a single registry (TestPyPI **or** PyPI) and performs a single action (dry **or** wet).

### Dry run

1. **Version audit** — Reads `pyproject.toml`, `__init__.py`, and `__main__.py`. Verifies all version strings match. Warns if only one source is found.
2. **Registry check** — Queries the target registry to confirm the version does not already exist.
3. **Token check** — Reads the token from `~/.pydeli/config.json`. If missing, guides you through creating one.
4. **Build** — Runs `uv build` in the app directory.
5. **Archive** — Copies `.whl` and `.tar.gz` to `<archive-dir>/<app-name>/`.

### Wet run

Steps 1–5 from dry run, plus:

6. **Upload** — Runs `uv publish` with the token injected via environment variable.
7. **Test-install (optional)** — pydeli asks if you want to verify. If yes: creates a temp venv, installs the package from the registry, opens it in a separate terminal window for you to test, waits for you to type `ok`, then cleans up.

## Configuration

### Config file

Stored at `~/.pydeli/config.json`. Created automatically on first run.

```json
{
  "tokens": {
    "my-app": {
      "testpypi": "pypi-...",
      "pypi": "pypi-..."
    }
  }
}
```

Tokens are stored per app, per registry. A token can be account-wide or project-scoped — pydeli does not distinguish between them.

### Token setup

When pydeli needs a token and none is stored, it prints step-by-step instructions:

1. The exact URL to visit on PyPI/TestPyPI.
2. What scope to select.
3. A masked prompt to paste the token.

The token is saved to `config.json` for future runs.

On every run, pydeli reminds you to switch from an account-wide token to a project-scoped token if you haven't already.

## Version requirements

pydeli checks version strings in these files:

- `pyproject.toml` — `[project].version`
- `src/<package>/__init__.py` — `__version__ = "..."`
- `src/<package>/__main__.py` — `__version__ = "..."`
- Also checks flat layout: `<package>/__init__.py`, `<package>/__main__.py`

All discovered version strings must be identical. pydeli does **not** modify these files — you manage version bumps yourself.

### PEP 440 version lifecycle

| Suffix | Meaning | Example |
|---|---|---|
| `.devN` | Development, not feature-complete | `1.2.3.dev1` |
| `aN` | Alpha, feature-complete but unstable | `1.2.3a1` |
| `bN` | Beta, mostly stable | `1.2.3b1` |
| `rcN` | Release candidate, believed bug-free | `1.2.3rc1` |
| *(none)* | Final release | `1.2.3` |
| `.postN` | Post-release, metadata corrections only | `1.2.3.post1` |

Use `.devN` suffixes for TestPyPI experiments. Once verified, drop the suffix and publish the clean version to PyPI.

## Archive structure

Artifacts are stored flat in `<archive-dir>/<app-name>/`:

```
releases/
  my-app/
    my_app-1.0.0-py3-none-any.whl
    my_app-1.0.0.tar.gz
    my_app-1.1.0-py3-none-any.whl
    my_app-1.1.0.tar.gz
```

Files are silently overwritten if the same version is built again (e.g., after a dry run followed by a wet run).

## Limitations

- **Verification terminal window**: On macOS, pydeli opens a new Terminal.app window for test-install verification. On Linux, it tries common terminal emulators (gnome-terminal, xfce4-terminal, konsole, xterm). On unsupported platforms, it prints manual instructions instead.
- **TestPyPI dependency resolution**: When test-installing from TestPyPI, dependencies are pulled from PyPI via `--extra-index-url`. If a dependency name collides between registries, the wrong version could be installed. This is a known TestPyPI limitation.
- **Single registry per run**: pydeli targets one registry at a time. Publishing to both TestPyPI and PyPI requires two separate runs.
- **Read-only**: pydeli never modifies your source files. Version bumps are your responsibility.

## Development

```bash
cd ~/code/shared/apps/pydeli

uv sync                    # install dependencies
uv run pydeli --help       # run the app
uv run pytest              # run tests
uv run ruff check .        # lint
uv run mypy src/pydeli/    # type check
```

## License

MIT
