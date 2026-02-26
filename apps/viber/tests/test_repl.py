"""Tests for REPL command parsing helpers."""

from viber.repl import _parse_id_token, _parse_pt_tokens


def test_parse_id_token_valid() -> None:
    assert _parse_id_token("g3", "g") == 3
    assert _parse_id_token("p12", "p") == 12
    assert _parse_id_token("t7", "t") == 7


def test_parse_id_token_wrong_prefix() -> None:
    assert _parse_id_token("g3", "p") is None


def test_parse_id_token_no_digits() -> None:
    assert _parse_id_token("g", "g") is None
    assert _parse_id_token("group", "g") is None


def test_parse_pt_tokens_p_first() -> None:
    pid, tid = _parse_pt_tokens("p3", "t5")
    assert pid == 3
    assert tid == 5


def test_parse_pt_tokens_t_first() -> None:
    pid, tid = _parse_pt_tokens("t5", "p3")
    assert pid == 3
    assert tid == 5


def test_parse_pt_tokens_invalid() -> None:
    pid, tid = _parse_pt_tokens("g1", "t2")
    assert pid is None
    assert tid is None


def test_parse_pt_tokens_uppercase() -> None:
    pid, tid = _parse_pt_tokens("P3", "T5")
    assert pid == 3
    assert tid == 5
