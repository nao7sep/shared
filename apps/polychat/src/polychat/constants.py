"""Application-level constants for PolyChat.

This module keeps only cross-cutting app/file/path constants.
"""

# ============================================================================
# Application identity
# ============================================================================

APP_NAME = "polychat"

# ============================================================================
# File extensions
# ============================================================================

CHAT_FILE_EXTENSION = ".json"
LOG_FILE_EXTENSION = ".log"

# ============================================================================
# Default directories and paths
# ============================================================================

# User data directory (created in home directory)
USER_DATA_DIR = f"~/.{APP_NAME}"

# REPL command history file
REPL_HISTORY_FILE = f"{USER_DATA_DIR}/history"

# Default directories for profile template
DEFAULT_CHATS_DIR = f"{USER_DATA_DIR}/chats"
DEFAULT_LOGS_DIR = f"{USER_DATA_DIR}/logs"

# Built-in prompt paths (relative to app root)
BUILTIN_PROMPT_SYSTEM_DEFAULT = "@/prompts/system/default.txt"
BUILTIN_PROMPT_TITLE = "@/prompts/title.txt"
BUILTIN_PROMPT_SUMMARY = "@/prompts/summary.txt"
BUILTIN_PROMPT_SAFETY = "@/prompts/safety.txt"

DATETIME_FORMAT_FILENAME = "%Y-%m-%d_%H-%M-%S"
