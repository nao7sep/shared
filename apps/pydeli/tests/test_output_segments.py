"""Tests for pydeli.output_segments module."""

from pydeli.output_segments import reset_segment_state, start_segment


class TestOutputSegments:
    def test_first_segment_no_blank(self):
        lines = []
        reset_segment_state()
        start_segment(output_fn=lambda s: lines.append(s))
        assert lines == []

    def test_second_segment_has_blank(self):
        lines = []
        reset_segment_state()
        start_segment(output_fn=lambda s: lines.append(s))
        start_segment(output_fn=lambda s: lines.append(s))
        assert lines == [""]

    def test_third_segment_has_two_blanks(self):
        lines = []
        reset_segment_state()
        start_segment(output_fn=lambda s: lines.append(s))
        start_segment(output_fn=lambda s: lines.append(s))
        start_segment(output_fn=lambda s: lines.append(s))
        assert lines == ["", ""]

    def test_reset_clears_state(self):
        lines = []
        reset_segment_state()
        start_segment(output_fn=lambda s: lines.append(s))
        reset_segment_state()
        start_segment(output_fn=lambda s: lines.append(s))
        assert lines == []
