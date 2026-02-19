# Installation: uv tool

Understanding how users install your CLI application with `uv tool`.

## Why uv tool?

Python installed via Homebrew (or system package managers) blocks direct `pip install` at the global level:

```
error: externally managed environment

This environment is externally managed
╰─> To install Python packages system-wide, try brew install...
    If you wish to install a Python application that isn't in Homebrew,
    it may be easiest to use 'pipx install xyz'
```

`uv tool` solves this cleanly:
- Creates a dedicated virtual environment for your app automatically
- Makes CLI commands globally available
- Keeps each tool's dependencies isolated from each other
- Works regardless of how Python was installed

## uv tool: The CLI App Installer

### What uv tool Does

```bash
uv tool install your-app
```

- Creates a dedicated virtual environment for your app
- Installs your app and its dependencies in isolation
- Makes the CLI command globally available
- No conflicts with other tools or system Python

### Installing uv

Users need uv installed first:

```bash
# macOS
brew install uv

# Or official installer (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Installation Instructions for Your README

### Recommended Structure

```markdown
## Installation

\`\`\`bash
uv tool install your-app
\`\`\`
```

### For TestPyPI Testing

```markdown
## Installation from TestPyPI

\`\`\`bash
uv tool install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  your-app
\`\`\`
```

**Why both indexes?**
- Your app is on TestPyPI
- Dependencies (like `openai`, `anthropic`) are on real PyPI
- `--extra-index-url` lets uv find dependencies

## uv tool Commands Reference

### Install

```bash
uv tool install your-app
uv tool install your-app==0.1.0  # Specific version
```

### Upgrade

```bash
uv tool upgrade your-app
uv tool upgrade --all  # Upgrade all tools
```

### Uninstall

```bash
uv tool uninstall your-app
```

### List Installed Tools

```bash
uv tool list
```

### Reinstall (Force)

```bash
uv tool install --force your-app
```

Useful when switching from TestPyPI to PyPI installation.

## Testing Installations

### After Installing

```bash
# Test CLI command exists
your-command --version
your-command --help

# Test basic functionality
your-command init
your-command status
```

### Verify Installation

```bash
uv tool list
# Shows: your-app 0.1.0
```

## Installation Troubleshooting

### "Command not found" After uv tool Install

**Cause**: uv tool bin directory not in PATH.

**Solution:**
```bash
# uv adds this automatically during install, but if missing:
export PATH="$HOME/.local/bin:$PATH"
# Then restart terminal or source ~/.zshrc
```

### "Module not found" When Running Command

**Cause**: Package structure issue in `pyproject.toml`.

**Check:**
```toml
[project.scripts]
your-command = "your_package.cli:main"
```

### Dependencies Not Installing from TestPyPI

**Cause**: Missing `--extra-index-url`.

**Solution:** Always include both indexes for TestPyPI:
```bash
uv tool install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  your-app
```

## Production Installation Workflow

### First Install (from PyPI)

```bash
uv tool install your-app
your-command --version
```

### Switching from TestPyPI to PyPI

```bash
# Remove TestPyPI version
uv tool uninstall your-app

# Install from PyPI
uv tool install your-app
```

### Upgrading to New Version

```bash
uv tool upgrade your-app
```

## Summary

- **uv tool**: Isolated environments, perfect for CLI apps, works with Homebrew Python
- **README**: One install command — `uv tool install your-app`
- **Testing**: Use the same method throughout testing and production

Next: [05-automation.md](05-automation.md) - Create scripts to automate the publishing workflow
