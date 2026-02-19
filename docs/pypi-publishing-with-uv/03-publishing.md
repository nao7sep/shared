# Publishing

Build, publish, test. Covers versioning, TestPyPI, production PyPI, and troubleshooting.

## Version Numbering

Semantic versioning (`MAJOR.MINOR.PATCH`):

```
0.0.x   Experimental — anything can change
0.1.0   First usable release
0.2.0   New features (minor)
0.2.1   Bug fix (patch)
1.0.0   Stable / production-ready (major)
```

**Critical rule**: versions are permanent on PyPI. Once published, that version number is burned forever — even if you delete the package.

## Publishing Workflow

### 1. Update Version

Edit `pyproject.toml`:

```toml
version = "0.2.0"
```

### 2. Build

```bash
rm -rf dist/
uv build
```

Creates `dist/your_app-0.2.0-py3-none-any.whl` and `dist/your_app-0.2.0.tar.gz`.

Verify contents: `tar -tzf dist/your_app-0.2.0.tar.gz`

### 3. Publish to TestPyPI

```bash
export UV_PUBLISH_TOKEN=<your-testpypi-token>
uv publish --publish-url https://test.pypi.org/legacy/
```

### 4. Test from TestPyPI

```bash
uv tool install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  your-app==0.2.0

your-command --version
```

Both indexes needed: your package from TestPyPI, dependencies from real PyPI.

### 5. Publish to PyPI

```bash
export UV_PUBLISH_TOKEN=<your-pypi-token>
uv publish
```

### 6. Test from PyPI

```bash
uv tool install your-app
your-command --version
```

### 7. Tag (Optional)

```bash
git tag v0.2.0
git push --tags
```

Not required for PyPI. Useful for tracking what's published, but can cause tag conflicts in monorepos with multiple apps.

## TestPyPI vs PyPI

| | TestPyPI | PyPI |
|---|----------|------|
| URL | https://test.pypi.org | https://pypi.org |
| Publish URL | `https://test.pypi.org/legacy/` | (default, no flag needed) |
| Purpose | Practice / verify | Production |
| Dependencies | Only your package; need `--extra-index-url` for deps | Everything available |
| Separate account | Yes | Yes |

**Always test on TestPyPI first.** First-time success rate is ~30%.

## Simple Repository API

URLs like `https://test.pypi.org/simple/` — this is the PEP 503 machine-readable index that uv/pip query. The `/project/` URLs are the human-readable web UI.

## Manual Publishing (No Script)

```bash
# Build
uv build

# TestPyPI
uv publish --publish-url https://test.pypi.org/legacy/

# PyPI
uv publish
```

## Troubleshooting

### "File already exists" / "Version already exists"

Version already published. Bump version in `pyproject.toml` and rebuild.

### "Authentication failed" / "Invalid credentials"

- Check `UV_PUBLISH_TOKEN` is set and starts with `pypi-`
- Verify token hasn't been revoked
- Ensure you're using the right token for the right index (TestPyPI vs PyPI)

### "Project name conflict"

Name too similar to existing package. Add a prefix/suffix to make it unique.

### Build contains wrong files

Verify `src/your_package/` exists and `name` in pyproject.toml matches. Check with `tar -tzf dist/*.tar.gz`.

## Publishing Checklist

- [ ] Version bumped in `pyproject.toml`
- [ ] `uv build` succeeds
- [ ] Package contents verified (`tar -tzf`)
- [ ] Published to TestPyPI
- [ ] Tested install from TestPyPI
- [ ] CLI commands work
- [ ] Published to PyPI
- [ ] Tested install from PyPI
- [ ] Version bump committed
- [ ] Git tag pushed (optional)

## Why Manual Over CI/CD?

- Simpler — no GitHub Actions complexity
- Monorepo-friendly — no tag conflicts between apps
- Full control over timing

Consider CI/CD when: multiple developers publishing, frequent releases, compliance requirements, or single-app repos.
