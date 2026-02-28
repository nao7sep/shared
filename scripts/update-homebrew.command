#!/bin/zsh
set -euo pipefail

# Update Homebrew and all packages
# This script installs Homebrew if not present, then updates everything

echo "Homebrew update"

# Check if Homebrew is installed
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

# Update Homebrew itself
echo ""
echo "Updating Homebrew..."
if brew update; then
    echo "Homebrew updated."
else
    echo "ERROR: Failed to update Homebrew."
    exit 1
fi

# Upgrade all packages
echo ""
echo "Upgrading installed packages..."
if brew upgrade; then
    echo "Installed packages upgraded."
else
    echo "ERROR: Failed to upgrade installed packages."
    exit 1
fi

# Clean up old versions
echo ""
echo "Cleaning up old versions..."
if brew cleanup; then
    echo "Cleanup complete."
else
    echo "ERROR: Failed to clean up old versions."
    exit 1
fi

echo ""
echo "Homebrew update complete."
