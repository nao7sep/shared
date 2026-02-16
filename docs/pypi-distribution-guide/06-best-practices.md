# Best Practices

Hard-learned lessons about dependency management, version constraints, and avoiding common pitfalls.

## Dependency Management

### List Only Direct Dependencies

In `pyproject.toml`, only list packages **you directly import** in your code:

```python
# Your code
import openai
import anthropic
from prompt_toolkit import prompt

# These should be in pyproject.toml:
# openai, anthropic, prompt-toolkit
```

**Don't list transitive dependencies** (dependencies of your dependencies). Poetry/pip resolves these automatically.

### Verifying Your Dependencies

Check what you actually import:

```bash
cd /path/to/your/app
grep -rh "^import \|^from " src/your_package --include="*.py" | \
  grep -v "^from your_package\." | \
  grep -v "^from \." | \
  sed 's/^import //; s/^from //; s/ .*//; s/\..*//;' | \
  sort -u
```

Compare this list to `[tool.poetry.dependencies]` - they should match (excluding standard library modules).

### Standard Library vs External

Python's standard library doesn't need to be listed:

```python
# Standard library (don't list in pyproject.toml)
import os
import sys
import json
import pathlib
import argparse

# External packages (DO list in pyproject.toml)  
import openai
import anthropic
```

## Version Constraints

### The Caret (^) Constraint

For applications, use caret (`^`) for compatible version ranges:

```toml
[tool.poetry.dependencies]
python = "^3.10"
openai = "^2.20.0"
```

**What `^` means:**
- `^2.20.0` allows: `2.20.1`, `2.21.0`, `2.99.0`
- `^2.20.0` blocks: `3.0.0` (major version bump)

This follows semantic versioning:
- **Major** (3.0.0): Breaking changes
- **Minor** (2.21.0): New features, backwards compatible
- **Patch** (2.20.1): Bug fixes

### Avoid >= (Too Permissive)

```toml
# Bad: Allows breaking changes
openai = ">=2.20.0"  # Accepts 3.0.0, 4.0.0, etc.

# Good: Allows compatible updates only
openai = "^2.20.0"   # Blocks 3.0.0
```

### Avoid Exact Pins (Too Strict)

```toml
# Bad: Prevents bug fixes
openai = "2.20.0"

# Good: Allows patches and minor updates
openai = "^2.20.0"
```

**Exception**: Pin exact versions only for:
- Known incompatibilities
- Critical security requirements
- Reproducible research environments

### Version Constraint Patterns

```toml
# Caret: Compatible updates (recommended for apps)
package = "^1.2.3"

# Tilde: Patch updates only
package = "~1.2.3"  # 1.2.4, 1.2.5, but not 1.3.0

# Wildcard: Latest in range
package = "1.2.*"

# Comparison: Fine-grained control
package = ">=1.2.0,<2.0.0"
```

### When to Update Version Minimums

After updating dependencies:

```bash
poetry update
```

Update `pyproject.toml` to reflect new minimums:

```toml
# Before poetry update
openai = "^2.20.0"

# After update (locked to 2.21.0)
openai = "^2.21.0"  # Update this
```

**Why?** Someone installing from source (without lock file) gets tested versions.

## Project Structure Best Practices

### Package Layout

```
your-app/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── your_package/      # Note: underscore, not hyphen
│       ├── __init__.py
│       ├── cli.py
│       └── data/          # Package data (included automatically)
│           └── defaults.json
├── tests/                 # Not included in package
├── docs/                  # Not included in package
└── tools/                 # Not included in package
```

### Naming Conventions

**Package name (pyproject.toml):**
```toml
name = "your-app"  # Use hyphens for PyPI
```

**Package directory:**
```python
src/your_package/  # Use underscores for Python
```

**Why different?** 
- PyPI names: Hyphens are conventional
- Python packages: Underscores required (hyphens aren't valid in imports)

### CLI Entry Points

```toml
[tool.poetry.scripts]
your-command = "your_package.cli:main"
```

- Script name: Use hyphens
- Python path: Use underscores
- Function: Typically named `main()`

## README Best Practices

### Installation Section

```markdown
## Installation

### Using pipx (Recommended)

\`\`\`bash
pipx install your-app
\`\`\`

### Using pip

\`\`\`bash
pip install your-app
\`\`\`
```

**Always list pipx first for CLI apps.**

### Quick Start After Installation

Show the most common first commands:

```markdown
## Quick Start

\`\`\`bash
# Initialize
your-app init

# Run
your-app start
\`\`\`
```

### Link to Full Documentation

```markdown
Full documentation: [docs/README.md](docs/README.md)
```

Don't overwhelm the main README - keep it focused on getting started.

## .gitignore Best Practices

### Repository Root

```gitignore
# Build artifacts (cross-language)
dist/
build/

# Python
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.pyc
*.pyo
*.pyd
.Python

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

### App-Level .gitignore

In monorepos, app-level `.gitignore` is usually unnecessary if repo root already covers common patterns. Only add app-specific ignores:

```gitignore
# App-specific only
local-config.json
*.local
```

## Common Pitfalls

### 1. Including Test Files in Package

**Problem:**
```toml
packages = [{include = "*", from = "."}]  # Too broad!
```

**Solution:**
```toml
packages = [{include = "your_package", from = "src"}]
```

Verify with: `tar -tzf dist/*.tar.gz`

### 2. Forgetting Package Data

**Problem:** Prompt files, configs not included.

**Solution:** Put data files inside the package:

```
src/your_package/
├── cli.py
└── data/       # Inside package = included
    └── prompts/
```

Not:
```
your-app/
├── src/your_package/
└── data/       # Outside package = excluded
```

### 3. Hardcoded Paths

**Problem:**
```python
# Breaks after installation
prompts_dir = Path("../../prompts")
```

**Solution:**
```python
# Works everywhere
prompts_dir = Path(__file__).parent / "data" / "prompts"
```

### 4. Version Number Mismatches

**Problem:** Publishing `0.1.0` but forgot to update `pyproject.toml`.

**Solution:** The publish script (from [05-automation.md](05-automation.md)) can verify version or auto-increment.

### 5. Publishing Without Testing

**Problem:** Skip TestPyPI, publish to PyPI, discover it's broken.

**Solution:** Always test with TestPyPI first, especially for:
- First release
- Major refactors
- Dependency changes
- Package structure changes

### 6. Secrets in Package

**Problem:** API keys, tokens accidentally included.

**Solution:**
- Use `.gitignore` for secret files
- Verify with `tar -tzf dist/*.tar.gz`
- Store secrets outside package
- Use environment variables or keychain

### 7. Platform-Specific Dependencies

**Problem:** Package works on macOS, fails on Linux.

**Solution:** Use conditional dependencies:

```toml
[tool.poetry.dependencies]
pywin32 = { version = "^306", markers = "platform_system == 'Windows'" }
```

### 8. Monorepo Git Tag Conflicts

**Problem:** Multiple apps in one repo, all using `v1.0.0` tags.

**Solution:**
- Use prefixed tags: `app1-v1.0.0`, `app2-v1.0.0`
- Or don't use tags, track versions in `pyproject.toml`
- Manual publishing (vs GitHub Actions) sidesteps this

## Testing Best Practices

### Test in Clean Environment

```bash
# Create temp venv
python3 -m venv /tmp/test-env
source /tmp/test-env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  your-app

# Test
your-command --help
your-command init

# Cleanup
deactivate
rm -rf /tmp/test-env
```

### Test with pipx

```bash
# Install
pipx install --index-url https://test.pypi.org/simple/ \
  --pip-args="--extra-index-url https://pypi.org/simple/" \
  your-app

# Test
your-command --help

# Cleanup
pipx uninstall your-app
```

## Documentation Structure

For CLI apps, this structure works well:

```
your-app/
├── README.md              # Quick start, installation
├── docs/
│   ├── README.md          # Documentation hub
│   ├── installation.md    # Detailed install guide
│   ├── usage.md           # Command reference
│   └── configuration.md   # Config file format
└── examples/              # Example configs, scripts
```

**README.md**: Brief, action-oriented, gets users started fast.
**docs/**: Comprehensive reference for all features.

## Release Checklist

Before publishing to production PyPI:

- [ ] Version incremented in `pyproject.toml`
- [ ] Dependencies up to date (`poetry update`)
- [ ] Dependency minimums updated (if needed)
- [ ] README reflects current version/features
- [ ] Tests pass (`poetry run pytest`)
- [ ] Built package (`poetry build`)
- [ ] Verified package contents (`tar -tzf dist/*.tar.gz`)
- [ ] Published to TestPyPI
- [ ] Tested installation from TestPyPI
- [ ] CLI commands work
- [ ] Ready to commit version bump
- [ ] Ready to tag release (optional)

## Monitoring Your Package

### After Publishing

1. **Check PyPI page**: https://pypi.org/project/your-app/
   - Description renders correctly
   - Links work
   - Dependencies listed

2. **Test installation**: On a different machine/environment

3. **Monitor download stats**: PyPI shows download counts (with delay)

### User Feedback

- Watch GitHub issues
- Monitor PyPI project page for questions
- Update documentation based on common questions

## Continuous Improvement

### Version 0.1.0 → 0.2.0

After first release:
- Collect user feedback
- Fix bugs (0.1.1, 0.1.2)
- Add features (0.2.0)
- Refine documentation

### Learning from Mistakes

Keep notes on what went wrong:
- Package structure issues
- Dependency conflicts
- Installation problems
- Documentation gaps

Use these to improve your process and help others.

## Summary

**Key Takeaways:**

1. **Dependencies**: List only direct imports, use `^` constraints
2. **Structure**: Package data inside src/package/, exclude tests
3. **Testing**: Always test with TestPyPI first
4. **Documentation**: Clear installation instructions, pipx first for CLI
5. **Workflow**: Use automation scripts, maintain checklists
6. **Monorepos**: Manual publishing avoids tag conflicts

## Further Reading

- [Poetry Documentation](https://python-poetry.org/docs/)
- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/)
- [Semantic Versioning](https://semver.org/)
- [PyPI Help](https://pypi.org/help/)
- [Python Packaging User Guide](https://packaging.python.org/)

## End of Guide

You now have a complete understanding of:
- PyPI fundamentals and TestPyPI
- Setting up accounts and credentials
- The publishing workflow
- pip vs pipx for installations
- Automation scripts
- Best practices and pitfalls

**Ready to publish!** Start with [02-setup.md](02-setup.md) if you haven't configured your accounts yet, or jump straight to publishing with [03-publishing.md](03-publishing.md).
