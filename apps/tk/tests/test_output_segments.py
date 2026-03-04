"""Tests for CLI output segment spacing helpers."""

from tk import __version__, cli
from tk.output_segments import start_output_segment


def test_start_output_segment_only_emits_blank_line_from_second_segment(capsys):
    start_output_segment()
    print("Before banner")
    start_output_segment()
    print("After banner")

    assert capsys.readouterr().out == "Before banner\n\nAfter banner\n"


def test_app_banner_has_no_leading_blank_when_first_segment(capsys):
    cli.print_app_banner()

    assert capsys.readouterr().out == f"tk {__version__}\n"


def test_app_banner_may_emit_leading_blank_when_not_first_segment(capsys):
    start_output_segment()
    print("Pre-banner message")

    cli.print_app_banner()

    assert capsys.readouterr().out == f"Pre-banner message\n\ntk {__version__}\n"
