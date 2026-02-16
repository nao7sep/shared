# Installation: pip vs pipx

Understanding how users install your package and why pipx is better for CLI applications.

## The Installation Landscape

When users install Python packages, they typically use:
- **pip** - The standard package installer
- **pipx** - A specialized installer for CLI applications

Your package description and README should guide users to the right tool.

## pip: The Standard Installer

### What pip Does

```bash
pip install your-app
```

- Installs package into current Python environment
- All dependencies go into the same environment
- Package code and dependencies mix with other installed packages

### The Problem with pip for CLI Apps

**Dependency conflicts:**

```bash
# User installs your CLI app
pip install your-app  # Requires openai==2.20.0

# Later, installs another tool
pip install other-tool  # Requires openai==3.0.0

# Result: One breaks!
```

**Global environment pollution:**
- Installing CLI tools clutters global Python environment
- Unrelated packages can interfere with each other
- No isolation between tools

### When pip Is Appropriate

- **Libraries** meant to be imported in code
- **Development dependencies** in a project
- **One-off scripts** you're testing
- **Inside virtual environments** (where isolation is already provided)

## pipx: The CLI App Installer

### What pipx Does

```bash
pipx install your-app
```

- Creates a dedicated virtual environment for your app
- Installs your app and its dependencies in isolation
- Makes CLI commands globally available
- Other apps can't interfere with your app's dependencies

### Why pipx for CLI Apps

**Isolation:**
```bash
pipx install app-one    # openai==2.20.0 in its own venv
pipx install app-two    # openai==3.0.0 in its own venv
# Both work! No conflicts.
```

**Clean global commands:**
- Your command is globally available (e.g., `your-app --help`)
- But the package itself is isolated
- Users don't think about virtual environments

**User-friendly:**
- Users don't need to manage venvs
- `pipx upgrade your-app` works cleanly
- `pipx uninstall your-app` removes everything

### Installing pipx

Users need pipx installed first:

```bash
# macOS
brew install pipx
pipx ensurepath

# Linux
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Windows
py -m pip install --user pipx
py -m pipx ensurepath
```

After installation, restart terminal or run the ensurepath command output.

## System Python Protection

Modern systems often protect their Python installation:

```
error: externally managed environment

This environment is externally managed
╰─> To install Python packages system-wide, try brew install...
    
    If you wish to install a Python application that isn't in Homebrew,
    it may be easiest to use 'pipx install xyz'
```

**Why this happens:**
- macOS/Linux Python is managed by the system package manager
- Direct `pip install` can break system tools
- PEP 668 enforces this protection

**This is actually good!** It pushes users toward pipx, which is the right tool for CLI apps.

## Installation Instructions for Your README

### Recommended Structure

```markdown
## Installation

### Using pipx (Recommended)

pipx install your-app

pipx installs CLI tools in isolated environments.

### Using pip

pip install your-app

Note: pipx is recommended to avoid dependency conflicts.
```

### For TestPyPI Testing

```markdown
## Installation from TestPyPI

### Using pipx

pipx install --index-url https://test.pypi.org/simple/ \
  --pip-args="--extra-index-url https://pypi.org/simple/" \
  your-app

### Using pip

pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  your-app
```

## pipx Commands Reference

### Install

```bash
pipx install your-app
pipx install your-app==0.1.0  # Specific version
```

### Upgrade

```bash
pipx upgrade your-app
pipx upgrade-all  # Upgrade all pipx apps
```

### Uninstall

```bash
pipx uninstall your-app
```

### List Installed Apps

```bash
pipx list
```

### Reinstall (Force)

```bash
pipx install --force your-app
```

Useful when switching from TestPyPI to PyPI installation.

## pip Commands Reference

### Install

```bash
pip install your-app
pip install your-app==0.1.0  # Specific version
```

### Upgrade

```bash
pip install --upgrade your-app
```

### Uninstall

```bash
pip uninstall your-app
```

### List Installed Packages

```bash
pip list
pip show your-app  # Detailed info
```

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

### Verify Installation Location

```bash
# With pipx
pipx list
# Shows: your-app 0.1.0 (isolated)

# With pip
pip show your-app
# Shows: Location: /path/to/site-packages
```

### Check Installed Files

```bash
# See what got installed
pip show -f your-app
```

## Installation Troubleshooting

### "Command not found" After pipx Install

**Cause**: `pipx ensurepath` not run, or terminal not restarted.

**Solution:**
```bash
pipx ensurepath
# Then restart terminal or:
source ~/.zshrc  # or ~/.bash_profile
```

### "Module not found" When Running Command

**Cause**: Package structure issue in `pyproject.toml`.

**Check:**
```toml
[tool.poetry]
packages = [{include = "your_package", from = "src"}]

[tool.poetry.scripts]
your-command = "your_package.cli:main"
```

### Dependencies Not Installing from TestPyPI

**Cause**: Missing `--extra-index-url`.

**Solution:** Always include both indexes for TestPyPI:
```bash
--index-url https://test.pypi.org/simple/ \
--extra-index-url https://pypi.org/simple/
```

### pipx vs pip Version Mismatch

If you installed with pip, then pipx:

```bash
# Remove pip version first
pip uninstall your-app

# Then install with pipx
pipx install your-app
```

## Best Practices

### For Package Authors

1. **Document pipx first** in your README
2. **Test with pipx** during development
3. **Explain why pipx** helps users understand
4. **Include both options** some users prefer pip

### For Users

1. **Use pipx for CLI tools** that provide commands
2. **Use pip for libraries** that you import in code
3. **Virtual environments with pip** if you must use pip for CLI tools
4. **Don't use sudo pip** - use pipx or `--user` flag

## Production Installation Workflow

### First Install (from PyPI)

```bash
# Recommended
pipx install your-app
your-command --version

# Or with pip
pip install your-app
your-command --version
```

### Switching from TestPyPI to PyPI

```bash
# Remove TestPyPI version
pipx uninstall your-app

# Install from PyPI
pipx install your-app
```

### Upgrading to New Version

```bash
# If using pipx
pipx upgrade your-app

# If using pip
pip install --upgrade your-app
```

## Summary

- **pipx**: Isolated environments, perfect for CLI apps, recommended
- **pip**: Direct installation, good for libraries, can cause conflicts
- **README**: Show pipx first, explain benefits
- **Testing**: Use same method (pipx/pip) throughout testing

Next: [05-automation.md](05-automation.md) - Create scripts to automate the publishing workflow
