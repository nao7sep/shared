# Project Structure

How to set up your project so it packages correctly.

## src Layout

```
your-app/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── your_package/        # underscore for Python package dir
│       ├── __init__.py
│       ├── cli.py
│       └── data/             # non-Python files auto-included if inside package
│           └── defaults.toml
├── tests/
├── scripts/
└── docs/
```

**Naming convention**: hyphens for PyPI name (`your-app`), underscores for Python package dir (`your_package`).

## pyproject.toml Essentials

```toml
[project]
name = "your-app"
version = "0.1.0"
description = "Short description"
readme = "README.md"
license = {file = "LICENSE"}
requires-python = ">=3.9"
dependencies = [
    "click>=8.0",
    "httpx",
]

[project.scripts]
your-command = "your_package.cli:main"

[build-system]
requires = ["uv_build"]
build-backend = "uv_build"
```

### Entry Points

`[project.scripts]` maps CLI command names to Python functions:

```toml
[project.scripts]
your-command = "your_package.cli:main"
```

After `uv tool install your-app`, running `your-command` invokes `your_package.cli.main()`.

### Conditional Dependencies (PEP 508 Markers)

```toml
[project]
dependencies = [
    "click>=8.0",
    "tzdata ; platform_system == 'Windows'",
    "uvloop ; platform_system != 'Windows'",
]
```

## What Gets Packaged

### Included

- `src/your_package/` (auto-detected by uv_build)
- Non-Python files inside the package dir (data files, templates, etc.)
- `README.md`
- `LICENSE`
- Generated metadata: `PKG-INFO`, `METADATA`

### Excluded

- `tests/`, `docs/`, `scripts/`
- `.venv/`, `__pycache__/`, `.pytest_cache/`
- Dev configs, dot files

### Verify Contents

```bash
uv build
tar -tzf dist/your_app-0.1.0.tar.gz
```

## Dependency Rules for Apps

- List only **direct** dependencies (not transitive)
- For apps (not libraries): skip version constraints, let uv resolve latest
- Pin only if a specific version is required for compatibility

### Updating Dependencies

```bash
uv lock --upgrade
uv sync
```

## .gitignore Additions

```gitignore
dist/
*.egg-info/
__pycache__/
.venv/
```

## Common Pitfalls

| Mistake | Fix |
|---------|-----|
| Test files in package | Keep `tests/` outside `src/` |
| Hardcoded paths | Use `Path(__file__).parent / "data"` for package data |
| Version mismatch (code vs pyproject.toml) | Single source of truth in `pyproject.toml` |
| Platform-specific deps without markers | Use PEP 508 environment markers |
