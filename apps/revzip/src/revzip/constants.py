"""Literal constants used by revzip."""

ARCHIVE_SUFFIX = ".zip"
METADATA_SUFFIX = ".json"

DEFAULT_IGNORE_NAMES = {
    ".git",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
}

UTC_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
LOCAL_DISPLAY_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
LOCAL_FILENAME_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"

MAIN_MENU_TEXT = "\n".join(
    (
        "1. Archive",
        "2. Extract",
        "3. Exit",
    )
)

LIST_SEPARATOR = " | "
WARNING_PREFIX = "WARNING:"
ERROR_PREFIX = "ERROR:"

# ASCII control chars (0-31, 127), spaces/newlines, and Windows-forbidden filename chars.
COMMENT_FILENAME_SANITIZE_REGEX = r"[\x00-\x1F\x7F /\\:*?\"<>|]+"
