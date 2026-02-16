# Setup: Accounts and Credentials

One-time setup for publishing to PyPI. Once configured, you won't need to repeat these steps.

## Prerequisites

- Poetry installed (`brew install poetry` on macOS)
- Python 3.10+ (check with `python3 --version`)
- A Python package ready to publish (with `pyproject.toml`)

## Step 1: Create PyPI Accounts

### TestPyPI Account

1. Go to https://test.pypi.org/account/register/
2. Fill out registration form
3. Verify email
4. **Enable 2FA** (Settings → Account Security → Two Factor Authentication)
   - Use authenticator app (Authy, Google Authenticator, etc.)
   - Save recovery codes securely

### PyPI Account  

1. Go to https://pypi.org/account/register/
2. Fill out registration form
3. Verify email
4. **Enable 2FA** (Settings → Account Security → Two Factor Authentication)

**Important**: These are separate accounts with separate databases. You need both.

## Step 2: Create API Tokens

### Why Tokens?

- Required for publishing (username/password doesn't work with Poetry/pip)
- More secure than passwords
- Can be scoped to specific projects
- Can be revoked without changing your password

### TestPyPI Token

1. Log in to https://test.pypi.org
2. Go to Account Settings → API tokens: https://test.pypi.org/manage/account/token/
3. Click "Add API token"
4. **Token name**: Your app name (e.g., `my-app`)
5. **Scope**: Choose "Entire account" (will scope to project after first upload)
6. Click "Add token"
7. **Copy the token** - starts with `pypi-` and is very long
8. **Save immediately** - you can't view it again

### PyPI Token

Same process as TestPyPI:

1. Log in to https://pypi.org
2. Go to Account Settings → API tokens: https://pypi.org/manage/account/token/
3. Create token with same settings
4. Copy and save

### Storing Tokens Securely

**Recommended: Keep in a secrets repository**

Create a file for Python-related secrets:

```bash
# Example: secrets/python/pypi-tokens.txt
TestPyPI Token:
pypi-AgEIcHlwaS5vcmcC...

PyPI Token:  
pypi-AgEIcHlwaS5vcmcC...
```

Store this in a private, encrypted git repository or password manager.

**Never commit tokens to your public repository!**

## Step 3: Configure Poetry with Tokens

Poetry can store tokens securely so you don't need to enter them every time.

### Configure TestPyPI Token

```bash
cd /path/to/your/app
poetry config pypi-token.testpypi pypi-YOUR_TESTPYPI_TOKEN_HERE
```

### Configure PyPI Token

```bash
poetry config pypi-token.pypi pypi-YOUR_PYPI_TOKEN_HERE
```

### Where Are Tokens Stored?

Poetry stores tokens in your system keychain (macOS/Linux) or credential manager (Windows):

- **macOS**: Keychain Access
- **Linux**: Secret Service / gnome-keyring
- **Windows**: Windows Credential Manager

You can view Poetry config with:
```bash
poetry config --list
```

## Step 4: Verify Poetry Setup

Check that Poetry is properly installed and configured:

```bash
poetry --version
# Should show: Poetry (version X.Y.Z)

poetry config --list
# Should show pypi-token entries (tokens are hidden)
```

## Step 5: Configure TestPyPI Repository

Poetry needs to know about TestPyPI as a separate repository:

```bash
cd /path/to/your/app
poetry config repositories.testpypi https://test.pypi.org/legacy/
```

This only needs to be done once per project.

## Token Scoping (After First Upload)

After successfully publishing version 1 to PyPI:

1. Go to https://pypi.org/manage/project/your-app/settings/
2. Delete the "entire account" token
3. Create a new token scoped to "Project: your-app"
4. Update Poetry config with new token:
   ```bash
   poetry config pypi-token.pypi pypi-NEW_SCOPED_TOKEN
   ```

This limits the token's access to just your app (more secure).

**Do the same for TestPyPI** after your first TestPyPI upload.

## Troubleshooting

### "Poetry not found"

```bash
# macOS with Homebrew
brew install poetry

# Or official installer
curl -sSL https://install.python-poetry.org | python3 -
```

### "Authentication failed"

- Verify token starts with `pypi-`
- Check you copied the entire token (they're very long)
- Ensure you're using the correct token (TestPyPI vs PyPI)
- Try reconfiguring: `poetry config pypi-token.pypi pypi-YOUR_TOKEN`

### "Repository not found"

Make sure you configured TestPyPI repository:
```bash
poetry config repositories.testpypi https://test.pypi.org/legacy/
```

## Credential Alternatives

### Environment Variables

Instead of storing in Poetry config:

```bash
# Set for one command
POETRY_PYPI_TOKEN_PYPI=pypi-YOUR_TOKEN poetry publish

# Or export for session
export POETRY_PYPI_TOKEN_PYPI=pypi-YOUR_TOKEN
poetry publish
```

### Keyring Setup

If Poetry's keyring integration fails, you may need to install keyring support:

```bash
pip install keyring
```

## Security Best Practices

1. **Enable 2FA** on both PyPI accounts
2. **Scope tokens** to projects after first upload
3. **Store tokens securely** (password manager or encrypted repo)
4. **Never commit** `.pypirc` files or tokens to git
5. **Rotate tokens** periodically (every 6-12 months)
6. **Revoke tokens** immediately if compromised

## Summary

You now have:
- ✅ TestPyPI and PyPI accounts with 2FA enabled
- ✅ API tokens for both services
- ✅ Poetry configured with tokens
- ✅ TestPyPI repository configured

Next: [03-publishing.md](03-publishing.md) - Learn the publishing workflow
