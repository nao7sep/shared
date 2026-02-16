# Publishing Workflow

The step-by-step process for building and publishing your package to PyPI.

## Prerequisites

From [02-setup.md](02-setup.md):
- PyPI and TestPyPI accounts configured
- API tokens stored in Poetry config
- TestPyPI repository configured

## The Publishing Process Overview

```
1. Update version in pyproject.toml
2. Build package (creates .whl and .tar.gz)
3. Publish to TestPyPI (test it works)
4. Test installation
5. Publish to PyPI (production)
```

## Step 1: Update Version

Edit `pyproject.toml`:

```toml
[tool.poetry]
name = "your-app"
version = "0.1.0"  # ← Change this
```

**Version naming:**
- First test: `0.0.1`, `0.0.2`, etc.
- First production: `0.1.0`
- Bug fixes: `0.1.1`, `0.1.2`
- New features: `0.2.0`, `0.3.0`
- Stable release: `1.0.0`

## Step 2: Build the Package

Navigate to your app directory:

```bash
cd /path/to/your/app
poetry build
```

This creates two files in `dist/`:
- `your_app-0.1.0-py3-none-any.whl` (wheel - preferred format)
- `your_app-0.1.0.tar.gz` (source distribution)

### Verify Build Contents

Check what's in the package:

```bash
tar -tzf dist/your_app-0.1.0.tar.gz
```

Ensure:
- ✅ Your Python code is there
- ✅ README.md and LICENSE included
- ✅ Any data files (prompts, configs) included
- ❌ No `tests/` or `__pycache__/`
- ❌ No secrets or sensitive files

### Clean Old Builds

If rebuilding, clean the `dist/` directory first:

```bash
rm -rf dist/
poetry build
```

Or if you have a cleanup script (see [05-automation.md](05-automation.md)), it can handle this.

## Step 3: Publish to TestPyPI

Always test on TestPyPI first:

```bash
poetry publish -r testpypi
```

- `-r testpypi`: Publishes to the TestPyPI repository we configured earlier
- Poetry will use your stored token automatically
- If successful, you'll see a URL to your package on TestPyPI

### Success Output

```
Publishing your-app (0.1.0) to testpypi
 - Uploading your_app-0.1.0-py3-none-any.whl 100%
 - Uploading your_app-0.1.0.tar.gz 100%
```

### View Your Package

Visit: `https://test.pypi.org/project/your-app/`

Check:
- Package description (from README)
- Version number
- Dependencies listed
- Install command shown

## Step 4: Test Installation

Before publishing to production, test that your package installs and works.

### Using pip

```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  your-app==0.1.0
```

**Why both indexes?**
- Your app is on TestPyPI
- Dependencies (like `openai`, `anthropic`) are on real PyPI
- `--extra-index-url` lets pip find dependencies

### Using pipx (For CLI Apps)

```bash
pipx install --index-url https://test.pypi.org/simple/ \
  --pip-args="--extra-index-url https://pypi.org/simple/" \
  your-app==0.1.0
```

See [04-installation.md](04-installation.md) for more on pip vs pipx.

### Test the Installation

```bash
# If it's a CLI app with a command
your-command --version

# Try basic functionality
your-command --help
your-command init
```

### If Testing Fails

Common issues:
- **Missing dependencies**: Check pyproject.toml lists all imports
- **Module not found**: Verify `packages` path in pyproject.toml
- **Command not found**: Check `[tool.poetry.scripts]` section
- **Data files missing**: Ensure they're in the package directory

Fix the issue, increment version (`0.0.2`), rebuild, and republish to TestPyPI.

## Step 5: Publish to PyPI (Production)

Once TestPyPI installation works perfectly:

```bash
poetry publish
```

**No `-r` flag needed** - publishes to PyPI by default.

### Confirmation Prompt

Poetry doesn't ask for confirmation! Once you hit Enter, it publishes.

**Best practice**: Use a helper script (see [05-automation.md](05-automation.md)) that asks for confirmation.

### Success Output

```
Publishing your-app (0.1.0) to PyPI
 - Uploading your_app-0.1.0-py3-none-any.whl 100%
 - Uploading your_app-0.1.0.tar.gz 100%
```

### View Your Package

Visit: `https://pypi.org/project/your-app/`

Your package is now publicly available!

## Step 6: Test Production Installation

Verify the production package works:

```bash
# Using pipx (recommended for CLI apps)
pipx install your-app

# Using pip
pip install your-app
```

No need for `--index-url` or `--extra-index-url` - everything is on PyPI now.

## Git Tagging (Optional)

Consider tagging releases in git:

```bash
git tag v0.1.0
git push --tags
```

**Benefits:**
- Links code state to published version
- Easy to see what code produced which release
- Can checkout old versions later

**Not required** for PyPI publishing, but helpful for project management.

## Common Publishing Errors

### "File already exists"

```
HTTPError: 400 Bad Request from https://upload.pypi.org/legacy/
File already exists.
```

**Cause**: You already published this version number.

**Solution**: You cannot re-upload the same version. Increment version and publish again.

```bash
# In pyproject.toml, change:
version = "0.1.0"  # to
version = "0.1.1"

# Then rebuild and publish
poetry build
poetry publish
```

### "Invalid credentials"

```
HTTP Error 403: Invalid or non-existent authentication information.
```

**Solutions:**
- Verify token is configured: `poetry config --list | grep pypi-token`
- Reconfigure token: `poetry config pypi-token.pypi pypi-YOUR_TOKEN`
- Check token hasn't been revoked in PyPI settings
- Ensure token has correct scope (entire account or project)

### "Project name conflict"

```
The name 'your-app' is too similar to an existing project.
```

**Cause**: Package name is too similar to existing package (PyPI prevents typosquatting).

**Solution**: Choose a more unique name. Try:
- Adding prefix: `mycompany-your-app`
- Adding suffix: `your-app-cli`
- Different naming: `your-application`

Update `name` in `pyproject.toml` and try again.

## Publishing Checklist

Before publishing to production PyPI:

- [ ] Version number updated in `pyproject.toml`
- [ ] `poetry build` succeeds without errors
- [ ] Checked package contents with `tar -tzf dist/*.tar.gz`
- [ ] Published to TestPyPI successfully
- [ ] Tested installation from TestPyPI
- [ ] CLI commands work (if applicable)
- [ ] Ready to commit version bump to git
- [ ] Prepared to tag release in git

## Workflow Summary

**For first release (0.0.1):**
```bash
# Edit pyproject.toml → version = "0.0.1"
poetry build
poetry publish -r testpypi
# Test installation from TestPyPI
poetry publish  # Production PyPI
```

**For subsequent releases:**
```bash
# Edit pyproject.toml → version = "0.1.0"
poetry build
poetry publish  # Skip TestPyPI if you're confident
```

**For testing iterations:**
```bash
# Edit pyproject.toml → version = "0.0.2"
poetry build
poetry publish -r testpypi
# Test, find issue, increment version, repeat
```

## Next Steps

- Learn about [04-installation.md](04-installation.md) - Installing packages with pip vs pipx
- Or skip to [05-automation.md](05-automation.md) - Create a helper script to automate this workflow
