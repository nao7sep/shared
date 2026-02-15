"""Central constants for PolyChat.

This module consolidates configuration constants and magic numbers.
"""

# ============================================================================
# Application identity
# ============================================================================

APP_NAME = "poly-chat"
APP_DISPLAY_NAME = "PolyChat"

# ============================================================================
# File extensions
# ============================================================================

CHAT_FILE_EXTENSION = ".json"
PROFILE_FILE_EXTENSION = ".json"
LOG_FILE_EXTENSION = ".log"
PROMPT_FILE_EXTENSION = ".txt"

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

# ============================================================================
# Display formatting
# ============================================================================

# Unified borderline style for chat context and REPL banners.
BORDERLINE_CHAR = "="
BORDERLINE_WIDTH = 80

# Search radius for smart text truncation
TRUNCATE_SEARCH_RADIUS = 10

# Display fallbacks for missing/invalid data
DISPLAY_UNKNOWN = "unknown"        # For timestamps, roles, models, status codes
DISPLAY_NONE = "none"              # For intentionally empty/null values
DISPLAY_MISSING_HEX_ID = "???"    # For missing message hex IDs

# ============================================================================
# History command
# ============================================================================

# Default number of messages shown by /history
HISTORY_DEFAULT_LIMIT = 10

# Default preview length for one-line truncated text displays
MESSAGE_PREVIEW_LENGTH = 100

# ============================================================================
# Date/time formats
# ============================================================================

DATETIME_FORMAT_FULL = "%Y-%m-%d %H:%M:%S"
DATETIME_FORMAT_SHORT = "%Y-%m-%d %H:%M"
DATETIME_FORMAT_FILENAME = "%Y-%m-%d_%H-%M-%S"

# ============================================================================
# Hex ID generation
# ============================================================================

# Minimum number of hex digits for message IDs
HEX_ID_MIN_DIGITS = 3

# Maximum attempts to generate unique hex ID before giving up
HEX_ID_MAX_ATTEMPTS = 3

# ============================================================================
# Display Emojis
# ============================================================================

# Role display emojis (used in /history command)
EMOJI_ROLE_USER = "🍼"
EMOJI_ROLE_ASSISTANT = "🚀"
EMOJI_ROLE_ERROR = "❌"
EMOJI_ROLE_UNKNOWN = "🃏"

# Mode banner emojis (REPL status indicators)
EMOJI_MODE_RETRY = "♻️"
EMOJI_MODE_SECRET = "🔒"

# State indicator emojis
EMOJI_WARNING = "⚠️"
