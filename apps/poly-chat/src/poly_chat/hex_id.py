"""Hex ID generation for message references.

This module provides functions to generate unique hex IDs for messages
in a chat session. Hex IDs are temporary (not saved to history) and
change on each app run.
"""

import random
from typing import Any, Set


def generate_hex_id(existing_ids: Set[str], min_digits: int = 3) -> str:
    """Generate unique hex ID.

    Args:
        existing_ids: Set of already used hex IDs (will be modified)
        min_digits: Minimum number of hex digits (default: 3)

    Returns:
        Unique hex ID string (e.g., "a3f", "b2c", "1a4f")

    The function tries to generate a hex ID with min_digits length.
    If all attempts fail (collisions), it increases the digit count
    and tries again.

    Capacity:
    - 3 digits: 4,096 unique IDs
    - 4 digits: 65,536 unique IDs
    """
    digits = min_digits
    max_attempts = 3

    while True:
        for _ in range(max_attempts):
            # Generate random hex
            hex_id = format(random.randint(0, 16**digits - 1), f'0{digits}x')
            if hex_id not in existing_ids:
                existing_ids.add(hex_id)
                return hex_id

        # All attempts failed, increase digits
        digits += 1


def is_hex_id(value: str) -> bool:
    """Check if a string looks like a hex ID.

    Args:
        value: String to check

    Returns:
        True if value is a valid hex ID format (3+ hex digits)
    """
    if not value:
        return False

    # Must not contain whitespace
    if any(c.isspace() for c in value):
        return False

    # Must be at least 3 characters
    if len(value) < 3:
        return False

    # Must be all hex digits
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def assign_hex_ids(
    message_count: int,
    existing_ids: Set[str]
) -> dict[int, str]:
    """Assign hex IDs to a range of messages.

    Args:
        message_count: Number of messages to assign IDs to
        existing_ids: Set of already used hex IDs (will be modified)

    Returns:
        Dictionary mapping message index to hex ID
    """
    hex_map = {}
    for i in range(message_count):
        hex_map[i] = generate_hex_id(existing_ids)
    return hex_map


def build_hex_map(messages: list[dict[str, Any]]) -> dict[int, str]:
    """Build index->hex_id map from message objects."""
    hex_map: dict[int, str] = {}
    for index, message in enumerate(messages):
        hid = message.get("hex_id")
        if isinstance(hid, str):
            hex_map[index] = hid
    return hex_map


def get_message_index(hex_id: str, source: list[dict[str, Any]] | dict[int, str]) -> int | None:
    """Get message index from hex ID.

    Args:
        hex_id: Hex ID to look up
        source: Message list (preferred) or index->hex_id map

    Returns:
        Message index, or None if not found
    """
    hex_map = build_hex_map(source) if isinstance(source, list) else source
    for index, hid in hex_map.items():
        if hid == hex_id:
            return index
    return None


def get_hex_id(index: int, source: list[dict[str, Any]] | dict[int, str]) -> str | None:
    """Get hex ID from message index.

    Args:
        index: Message index
        source: Message list (preferred) or index->hex_id map

    Returns:
        Hex ID, or None if not found
    """
    hex_map = build_hex_map(source) if isinstance(source, list) else source
    return hex_map.get(index)
