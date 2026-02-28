#!/bin/zsh
set -euo pipefail

# Update Python and uv
# This script ensures Homebrew, Python, and uv are installed via Homebrew,
# then updates Python and uv to their latest versions

echo "Python and uv update"

# Check if Homebrew is installed (needed for Python and uv)
echo ""
echo "Checking Homebrew installation..."
if command -v brew &> /dev/null; then
    echo "Homebrew is installed."
else
    echo "Installing Homebrew."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Detect architecture and set Homebrew path
    if [[ $(uname -m) == 'arm64' ]]; then
        BREW_PATH="/opt/homebrew/bin/brew"
    else
        BREW_PATH="/usr/local/bin/brew"
    fi

    # Add Homebrew to PATH in shell profile (with newline before)
    if ! grep -q "eval.*brew shellenv" ~/.zprofile 2>/dev/null; then
        echo "" >> ~/.zprofile
        echo "eval \"\$($BREW_PATH shellenv)\"" >> ~/.zprofile
        echo "Added Homebrew to ~/.zprofile."
    fi

    # Apply for current session
    eval "$($BREW_PATH shellenv)"

    echo "Homebrew installed."
fi

# Check if Python is installed via Homebrew
echo ""
echo "Checking Python installation..."
if brew list python &> /dev/null; then
    echo "Python is installed via Homebrew."
else
    echo "Installing Python via Homebrew."
    if brew install python; then
        echo "Python installed."
    else
        echo "ERROR: Failed to install Python."
        exit 1
    fi
fi

# Check if uv is installed via Homebrew
echo ""
echo "Checking uv installation..."
if brew list uv &> /dev/null; then
    echo "uv is installed via Homebrew."
else
    echo "Installing uv via Homebrew."
    if brew install uv; then
        echo "uv installed."
    else
        echo "ERROR: Failed to install uv."
        exit 1
    fi
fi

# Update Python
echo ""
echo "Updating Python..."
if brew upgrade python || brew upgrade python@3; then
    echo "Python updated."
else
    echo "ERROR: Failed to update Python."
    exit 1
fi

# Update uv
echo ""
echo "Updating uv..."
if brew upgrade uv; then
    echo "uv updated."
else
    echo "ERROR: Failed to update uv."
    exit 1
fi

echo ""
echo "Python and uv update complete."
