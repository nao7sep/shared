#!/bin/bash

# Launch tk for shared repo tasks
# Profile and data are stored in secrets repo, TODO.md is in shared repo

set -e  # Exit on any error

PROFILE_PATH="$HOME/code/shared/apps/tk/data/profile.json"

echo ""
echo "=== tk: shared repo tasks ==="
echo ""

# Check if profile exists
if [ ! -f "$PROFILE_PATH" ]; then
    echo "✗ Profile not found: $PROFILE_PATH"
    echo ""
    echo "Please ensure the profile file exists in the secrets repo."
    echo ""
    exit 1
fi

# Get the tk project directory
TK_DIR="$HOME/code/shared/apps/tk"

# Check if in virtual environment, if not use poetry run
if [ -z "$VIRTUAL_ENV" ]; then
    cd "$TK_DIR"
    poetry run tk --profile "$PROFILE_PATH"
else
    tk --profile "$PROFILE_PATH"
fi
