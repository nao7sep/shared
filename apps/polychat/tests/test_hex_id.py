"""Tests for hex_id module."""

import pytest
from polychat.hex_id import (
    generate_hex_id,
    is_hex_id,
    assign_hex_ids,
    get_message_index,
    get_hex_id,
)


def test_generate_hex_id_basic():
    """Test basic hex ID generation."""
    existing = set()
    hex1 = generate_hex_id(existing)

    # Should be 3 digits
    assert len(hex1) == 3
    # Should be valid hex
    assert is_hex_id(hex1)
    # Should be added to existing set
    assert hex1 in existing


def test_generate_hex_id_uniqueness():
    """Test that generated hex IDs are unique."""
    existing = set()
    ids = [generate_hex_id(existing) for _ in range(100)]

    # All should be unique
    assert len(ids) == len(set(ids))
    # All should be in existing set
    assert len(existing) == 100


def test_generate_hex_id_collision_handling():
    """Test that hex ID generation handles collisions by increasing digits."""
    existing = set()

    # Fill up 3-digit space (4096 IDs)
    # We'll generate a lot of IDs and verify it increases digits when needed
    for _ in range(5000):
        hex_id = generate_hex_id(existing)
        assert hex_id in existing

    # Should have some 4-digit IDs now
    four_digit_ids = [hid for hid in existing if len(hid) == 4]
    assert len(four_digit_ids) > 0


def test_is_hex_id_valid():
    """Test is_hex_id with valid inputs."""
    assert is_hex_id("a3f")
    assert is_hex_id("b2c")
    assert is_hex_id("000")
    assert is_hex_id("fff")
    assert is_hex_id("1a4f")
    assert is_hex_id("abcd")


def test_is_hex_id_invalid():
    """Test is_hex_id with invalid inputs."""
    assert not is_hex_id("")
    assert not is_hex_id("ab")  # Too short
    assert not is_hex_id("xyz")  # Not hex
    assert not is_hex_id("12g")  # Not hex
    assert not is_hex_id("last")  # Not hex
    assert not is_hex_id("123 ")  # Contains space


def test_assign_hex_ids():
    """Test bulk hex ID assignment."""
    existing = set()
    hex_map = assign_hex_ids(10, existing)

    # Should have 10 entries
    assert len(hex_map) == 10
    # Should have indices 0-9
    assert set(hex_map.keys()) == set(range(10))
    # All values should be unique
    assert len(set(hex_map.values())) == 10
    # All should be valid hex IDs
    for hex_id in hex_map.values():
        assert is_hex_id(hex_id)


def test_get_message_index():
    """Test getting message index from hex ID."""
    hex_map = {0: "a3f", 1: "b2c", 2: "1d4"}

    assert get_message_index("a3f", hex_map) == 0
    assert get_message_index("b2c", hex_map) == 1
    assert get_message_index("1d4", hex_map) == 2
    assert get_message_index("xyz", hex_map) is None
    assert get_message_index("", hex_map) is None


def test_get_hex_id():
    """Test getting hex ID from message index."""
    hex_map = {0: "a3f", 1: "b2c", 2: "1d4"}

    assert get_hex_id(0, hex_map) == "a3f"
    assert get_hex_id(1, hex_map) == "b2c"
    assert get_hex_id(2, hex_map) == "1d4"
    assert get_hex_id(3, hex_map) is None
    assert get_hex_id(-1, hex_map) is None


def test_hex_id_workflow():
    """Test a complete workflow with hex IDs."""
    existing = set()

    # Generate IDs for 5 messages
    hex_map = assign_hex_ids(5, existing)

    # Look up by hex ID
    hex_id_of_msg_2 = hex_map[2]
    assert get_message_index(hex_id_of_msg_2, hex_map) == 2

    # Add a new message
    new_hex = generate_hex_id(existing)
    hex_map[5] = new_hex

    # Verify new message can be found
    assert get_message_index(new_hex, hex_map) == 5
    assert get_hex_id(5, hex_map) == new_hex


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
