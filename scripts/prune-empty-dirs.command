#!/bin/bash

set -euo pipefail

# Relative paths from repo root to skip.
SKIP_PATHS=(
  ".git/"
)

# File names that are ignored when deciding whether a directory is effectively empty.
# Keep entries lowercase; matching is case-insensitive.
JUNK_FILENAMES=(
  ".ds_store"
  "thumbs.db"
  "desktop.ini"
)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Include hidden files in glob expansion and return an empty list for empty dirs.
shopt -s dotglob nullglob

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

is_skipped() {
  local rel_path="$1"
  local skip_path

  for skip_path in "${SKIP_PATHS[@]}"; do
    local normalized_skip="${skip_path%/}/"
    if [[ "$rel_path" == "$normalized_skip"* ]]; then
      return 0
    fi
  done

  return 1
}

is_junk_file() {
  local file_name_lower
  local junk_name

  file_name_lower="$(to_lower "$1")"

  for junk_name in "${JUNK_FILENAMES[@]}"; do
    if [[ "$file_name_lower" == "$junk_name" ]]; then
      return 0
    fi
  done

  return 1
}

prune_directory_if_allowed() {
  local dir="$1"
  local entry
  local file_name
  local -a entries=()
  local -a junk_files=()

  entries=( "$dir"/* )

  # True empty directory.
  if [[ "${#entries[@]}" -eq 0 ]]; then
    rmdir "$dir" 2>/dev/null || return 1
    return 0
  fi

  # Directory is prunable only if every entry is a junk file.
  for entry in "${entries[@]}"; do
    if [[ -d "$entry" ]]; then
      return 1
    fi

    if [[ ! -f "$entry" ]]; then
      return 1
    fi

    file_name="$(basename "$entry")"
    if is_junk_file "$file_name"; then
      junk_files+=( "$entry" )
    else
      return 1
    fi
  done

  rm -f -- "${junk_files[@]}"
  deleted_junk_file_count=$((deleted_junk_file_count + ${#junk_files[@]}))

  rmdir "$dir" 2>/dev/null || return 1
  return 0
}

echo "Repo root: $REPO_ROOT"
echo "Pruning empty directories and directories that only contain junk files..."

deleted_dir_count=0
deleted_junk_file_count=0

while IFS= read -r -d '' dir; do
  [[ "$dir" == "." ]] && continue

  rel_dir="${dir#./}"
  rel_dir="${rel_dir%/}/"

  if is_skipped "$rel_dir"; then
    continue
  fi

  if prune_directory_if_allowed "$dir"; then
    echo "Removed: $rel_dir"
    deleted_dir_count=$((deleted_dir_count + 1))
  fi
done < <(find . -depth -type d -print0)

echo "Done. Removed $deleted_dir_count directories and $deleted_junk_file_count junk files."
