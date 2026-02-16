# PyPI Basics

Understanding Python package distribution fundamentals before you start publishing.

## What is PyPI?

**PyPI (Python Package Index)** is the official repository for Python packages. When users run `pip install your-package`, pip downloads it from PyPI.

- **Website**: https://pypi.org
- **Purpose**: Central repository for all public Python packages
- **Free**: No cost to publish or download packages

## TestPyPI: The Practice Server

**TestPyPI** is a separate instance of PyPI for testing:

- **Website**: https://test.pypi.org  
- **Purpose**: Practice publishing without affecting production
- **Separate database**: Packages published here don't appear on real PyPI
- **Missing dependencies**: Only YOUR package is on TestPyPI; dependencies (like `openai`, `anthropic`) must come from real PyPI

### Why Use TestPyPI?

- **Safe testing**: Mistakes don't affect production
- **Learn the workflow**: Practice the publish process
- **Catch packaging errors**: Verify your package installs correctly
- **First-time publishers**: ~30% success rate on first try - TestPyPI lets you iterate

### TestPyPI Installation Pattern

Because dependencies aren't on TestPyPI, you need both indexes:

```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  your-package
```

- `--index-url`: Primary source (TestPyPI for your package)
- `--extra-index-url`: Fallback source (PyPI for dependencies)

## Version Numbering

PyPI uses **semantic versioning** (semver):

```
MAJOR.MINOR.PATCH
  1  .  2  .  3
```

### Rules

- **MAJOR**: Breaking changes (e.g., 1.x.x → 2.0.0)
- **MINOR**: New features, backwards compatible (e.g., 1.2.x → 1.3.0)
- **PATCH**: Bug fixes (e.g., 1.2.3 → 1.2.4)

### Pre-1.0 Versions

```
0.0.x   Experimental/testing - anything can change
0.1.0   First usable release
0.2.0   Adding features
1.0.0   Stable, production-ready
```

### Important Version Rules

1. **Versions are permanent**: Once published, you cannot change or delete a version number
2. **Can delete packages**: You can remove the entire package, but version numbers are still "burned"
3. **Must increment**: To fix issues, publish a new version (e.g., 0.1.1)

**Example workflow:**
- Publish `0.0.1` to TestPyPI → fails
- Fix issue, publish `0.0.2` to TestPyPI → works!
- Publish `0.0.2` (or `0.1.0`) to production PyPI

## What Gets Packaged?

### Included by Default

Only what's specified in `pyproject.toml`:

```toml
[tool.poetry]
packages = [{include = "your_package", from = "src"}]
readme = "README.md"
license = "LICENSE"
```

This means:
- ✅ `src/your_package/` (your code)
- ✅ `README.md`
- ✅ `LICENSE`
- ❌ `tests/`, `docs/`, `tools/` (excluded automatically)
- ❌ `.venv/`, `__pycache__/` (build artifacts - always excluded)

### Package Data (Files Within Your Package)

If you have non-Python files inside your package:

```
src/your_package/
├── __init__.py
├── cli.py
└── prompts/          # ← These files
    ├── default.txt
    └── system.txt
```

Poetry includes them automatically! Just ensure they're inside the package directory specified in `pyproject.toml`.

### Verifying Package Contents

After building, check what's included:

```bash
tar -tzf dist/your-package-0.1.0.tar.gz
```

Look for:
- Your Python files
- README and LICENSE
- Any data files you expect
- Ensure no test files or secrets leaked

## The Simple Repository API

You might see URLs like `https://pypi.org/simple/` - this is the **PEP 503 Simple Repository API**:

- **Purpose**: Machine-readable package index for pip
- **vs Web UI**: `pypi.org/project/name/` is for humans, `/simple/` is for tools
- **Standard**: All Python package repositories implement this API

When you see `/simple/` in pip commands, that's the technical endpoint pip uses to:
- List package versions
- Get download URLs  
- Fetch metadata

## GitHub Actions vs Manual Publishing

The conversation that led to this guide initially explored GitHub Actions automation but chose manual publishing because:

### Why Manual Won

- ✅ **Simpler**: No CI/CD complexity
- ✅ **Monorepo-friendly**: No tag conflicts between multiple apps
- ✅ **Full control**: You decide exactly when to publish
- ✅ **Learning**: You understand what's happening at each step

### When to Use GitHub Actions

- Multiple developers publishing
- Frequent releases (daily/weekly)
- Need reproducible builds for compliance
- Apps in separate repositories (not monorepos)

## File Structure Context

This guide assumes a monorepo structure:

```
your-repo/
├── apps/
│   ├── app1/
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   └── tools/
│   └── app2/
│       ├── pyproject.toml
│       └── src/
└── docs/
```

**Why this matters:**
- GitHub Actions workflows at repo root get messy with multiple apps
- Need app-specific tags (e.g., `app1-v1.0.0`) to avoid conflicts
- Manual publishing sidesteps these issues entirely

## Next Steps

Now that you understand the basics, proceed to [02-setup.md](02-setup.md) to set up your PyPI accounts and credentials.
