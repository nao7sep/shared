"""Tests for emojihunt.reporter — sorting, escaping, and file format edge cases."""

from __future__ import annotations

from pathlib import Path

from emojihunt.models import (
    EmojiMetadata,
    HandledPath,
    HandledPathStatus,
    RiskLevel,
    ScanContext,
    ScanFinding,
)
from emojihunt.reporter import generate_catalog, generate_handled_paths_file, generate_scan_report


def _make_metadata(
    char: str = "\U0001F600",
    code_points: str = "U+1F600",
    name: str = "grinning face",
    risk_level: RiskLevel = RiskLevel.SAFE,
) -> EmojiMetadata:
    return EmojiMetadata(
        char=char,
        code_points=code_points,
        name=name,
        unicode_version="6.1",
        risk_level=risk_level,
        risk_reasons=[],
    )


def _make_context(**overrides: object) -> ScanContext:
    defaults = dict(
        targets=["/src"],
        ignore_file=None,
        started_utc="2026-03-13T00:00:00.000000Z",
        finished_utc="2026-03-13T00:00:01.000000Z",
        started_local="2026-03-13 09:00:00",
        finished_local="2026-03-13 09:00:01",
        duration_seconds=1.0,
        files_scanned=10,
        files_skipped=1,
        files_errored=0,
        unique_emojis_found=2,
        total_occurrences=5,
    )
    defaults.update(overrides)
    return ScanContext(**defaults)  # type: ignore[arg-type]


def _extract_tbody(html: str) -> str:
    """Extract just the tbody section to avoid matching CSS/JS/metadata."""
    start = html.index("<tbody>")
    end = html.index("</tbody>") + len("</tbody>")
    return html[start:end]


class TestScanReportSorting:
    def test_sorted_by_count_desc_then_code_points_asc(self, tmp_path: Path) -> None:
        """Primary sort: occurrence count descending.
        Tiebreaker: code points ascending."""
        findings = [
            ScanFinding(_make_metadata(code_points="U+AAAA"), occurrence_count=3),
            ScanFinding(_make_metadata(code_points="U+BBBB"), occurrence_count=5),
            ScanFinding(_make_metadata(code_points="U+CCCC"), occurrence_count=3),
        ]
        out = tmp_path / "report.html"
        generate_scan_report(findings, _make_context(), out)

        tbody = _extract_tbody(out.read_text(encoding="utf-8"))
        pos_bbbb = tbody.index("U+BBBB")
        pos_aaaa = tbody.index("U+AAAA")
        pos_cccc = tbody.index("U+CCCC")
        assert pos_bbbb < pos_aaaa  # higher count first
        assert pos_aaaa < pos_cccc  # same count, lower code point first


class TestHtmlEscaping:
    def test_html_special_chars_in_name_escaped(self, tmp_path: Path) -> None:
        """Names containing < > & must be escaped in the table body."""
        m = _make_metadata(name='<b>bold&"quoted"</b>')
        out = tmp_path / "catalog.html"
        generate_catalog([m], out)

        tbody = _extract_tbody(out.read_text(encoding="utf-8"))
        assert "<b>" not in tbody
        assert "&lt;b&gt;" in tbody
        assert "&amp;" in tbody


class TestRiskLevelRowClasses:
    def test_red_row_has_css_class(self, tmp_path: Path) -> None:
        m = _make_metadata(risk_level=RiskLevel.RED)
        out = tmp_path / "catalog.html"
        generate_catalog([m], out)

        html = out.read_text(encoding="utf-8")
        assert 'class="risk-red"' in html

    def test_safe_row_has_no_risk_class(self, tmp_path: Path) -> None:
        m = _make_metadata(risk_level=RiskLevel.SAFE)
        out = tmp_path / "catalog.html"
        generate_catalog([m], out)

        tbody = _extract_tbody(out.read_text(encoding="utf-8"))
        # SAFE rows in the data table should have no risk class
        assert "risk-red" not in tbody
        assert "risk-yellow" not in tbody


class TestHandledPathsFile:
    def test_sorted_alphabetically(self, tmp_path: Path) -> None:
        paths = [
            HandledPath("/z/file.txt", HandledPathStatus.OK),
            HandledPath("/a/file.txt", HandledPathStatus.OK),
            HandledPath("/m/file.txt", HandledPathStatus.SKIPPED),
        ]
        out = tmp_path / "paths.txt"
        generate_handled_paths_file(paths, out)

        lines = out.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "/a/file.txt"
        assert lines[1] == "/m/file.txt | SKIPPED"
        assert lines[2] == "/z/file.txt"

    def test_empty_list_produces_empty_file(self, tmp_path: Path) -> None:
        out = tmp_path / "paths.txt"
        generate_handled_paths_file([], out)
        assert out.read_text(encoding="utf-8") == ""

    def test_error_with_message_formatted(self, tmp_path: Path) -> None:
        paths = [
            HandledPath("/bad/file.txt", HandledPathStatus.ERROR, "Permission denied"),
        ]
        out = tmp_path / "paths.txt"
        generate_handled_paths_file(paths, out)

        content = out.read_text(encoding="utf-8")
        assert "/bad/file.txt | ERROR: Permission denied" in content


class TestMultiLineHtmlForGitDiff:
    """Each table row must span multiple lines so git diffs isolate
    individual cell changes."""

    def test_each_td_on_separate_line(self, tmp_path: Path) -> None:
        m = _make_metadata()
        out = tmp_path / "catalog.html"
        generate_catalog([m], out)

        lines = out.read_text(encoding="utf-8").splitlines()
        # Find the <tr> block — it should have separate <td> lines
        tr_indices = [i for i, l in enumerate(lines) if "<tr" in l]
        # The data row (not header) should have multiple <td> children on separate lines
        data_tr = [i for i in tr_indices if "tbody" not in lines[i] and "thead" not in lines[i]]
        assert len(data_tr) >= 1
        # The line after <tr> should be a <td>, not another <tr>
        first_data_row = data_tr[0]
        assert "<td" in lines[first_data_row + 1]


class TestSelfContainedHtml:
    def test_embedded_css_and_js(self, tmp_path: Path) -> None:
        """HTML must be fully self-contained — embedded <style> and <script>."""
        m = _make_metadata()
        out = tmp_path / "catalog.html"
        generate_catalog([m], out)

        html = out.read_text(encoding="utf-8")
        assert "<style>" in html
        assert "<script>" in html
        assert "sortTable" in html  # JS function present
        assert 'rel="stylesheet"' not in html  # no external CSS
