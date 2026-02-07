# Path Security Audit

**Date:** 2026-02-07
**Status:** ✓ PASSED

## Overview

This document records the security audit of path handling in PolyChat to ensure no current directory vulnerabilities exist.

## Audit Results

### ✓ No Current Directory Usage

**Searched for:**
- `Path.cwd()` - Not found
- `os.getcwd()` - Not found
- `Path(".")` - Not found

**Result:** No current working directory references found in codebase.

### ✓ Central Path Validation

All user-provided paths go through `profile.map_path()` which:
- ✓ Accepts `~` and `~/...` (home directory)
- ✓ Accepts `@` and `@/...` (app root directory)
- ✓ Accepts absolute paths
- ✓ **REJECTS** relative paths without prefix
- ✓ Provides clear error messages with guidance

### ✓ File Operations Security

All file operation functions expect "already mapped" paths:

| Function | File | Security |
|----------|------|----------|
| `load_chat()` | chat.py | ✓ Expects absolute path |
| `save_chat()` | chat.py | ✓ Expects absolute path |
| `generate_chat_filename()` | chat_manager.py | ✓ Receives chats_dir from profile |
| `load_from_json()` | keys/json_files.py | ✓ Expects absolute path |

### ✓ Profile Loading Chain

User paths → `load_profile()` → `map_path()` → Absolute paths

This ensures all paths are validated before use:
1. `profile["chats_dir"]` - Mapped through `map_path()`
2. `profile["log_dir"]` - Mapped through `map_path()`
3. `profile["system_prompt"]` - Mapped through `map_path()`
4. API key JSON paths - Mapped through `map_path()`

### ✓ Command Validation

The `/system` command validates paths:
- Rejects relative paths without `~` or `@` prefix
- Returns clear error messages
- Uses `map_path()` for validation

## Test Coverage

**New tests:** `tests/test_path_security.py` (10 tests)

Tests verify:
- Relative paths are rejected
- `~` prefix works correctly
- `@` prefix works correctly
- Absolute paths are accepted
- Current directory is never used
- Error messages are helpful

## Security Guarantees

✓ **No directory traversal vulnerabilities** - Relative paths cannot reach parent directories
✓ **No current directory exposure** - Working directory doesn't affect file operations
✓ **Predictable behavior** - All paths are explicitly specified with clear semantics
✓ **Clear error messages** - Users get helpful guidance when paths are invalid

## Recommendations

1. ✓ Continue using `map_path()` for all user-provided paths
2. ✓ Document "already mapped" in function signatures that accept paths
3. ✓ Maintain test coverage for path security
4. ⚠️ Consider adding validation in file operation functions to double-check paths are absolute (defense in depth)

## Conclusion

**The codebase is secure against current directory vulnerabilities.**

All paths are properly validated, and there is no use of current working directory in the codebase.
