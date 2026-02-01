#!/bin/bash

# Make all .command files in the repository executable
# This is useful after cloning or when git doesn't preserve execute permissions

set -e  # Exit on any error

# Get the repository root (parent of tools directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo ""
echo "=== Fix .command File Permissions ==="
echo ""
echo "Repository: $REPO_ROOT"
echo ""

# Find all .command files
echo "Searching for .command files..."
COMMAND_FILES=$(find "$REPO_ROOT" -type f -name "*.command" 2>/dev/null)

if [ -z "$COMMAND_FILES" ]; then
    echo "✓ No .command files found"
    echo ""
    exit 0
fi

# Count files
FILE_COUNT=$(echo "$COMMAND_FILES" | wc -l | tr -d ' ')
echo "Found $FILE_COUNT .command file(s):"
echo ""

# Show files with their current permissions
echo "$COMMAND_FILES" | while IFS= read -r file; do
    PERMS=$(ls -lh "$file" | awk '{print $1}')
    REL_PATH="${file#$REPO_ROOT/}"
    echo "  $PERMS  $REL_PATH"
done

echo ""
read -p "Make these files executable? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    echo ""
    exit 0
fi

# Make files executable
echo ""
echo "Setting execute permissions..."
UPDATED=0

echo "$COMMAND_FILES" | while IFS= read -r file; do
    if [ ! -x "$file" ]; then
        chmod +x "$file"
        REL_PATH="${file#$REPO_ROOT/}"
        echo "  ✓ $REL_PATH"
        UPDATED=$((UPDATED + 1))
    fi
done

echo ""
echo "=== Done! ==="
echo ""
