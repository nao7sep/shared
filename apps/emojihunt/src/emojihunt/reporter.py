"""HTML and text file report generation.

Generates self-contained HTML files with embedded CSS and JavaScript for
sorting and filtering. Multi-line HTML formatting ensures clean git diffs.
Knows nothing about scanning or emoji detection.
"""

from __future__ import annotations

import html
from pathlib import Path

from .models import (
    EmojiMetadata,
    HandledPath,
    RiskLevel,
    ScanContext,
    ScanFinding,
)

# CSS class names for risk-level row backgrounds
_RISK_CSS_CLASSES = {
    RiskLevel.RED: "risk-red",
    RiskLevel.YELLOW: "risk-yellow",
    RiskLevel.SAFE: "",
}

_CSS = """\
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: #1a1a1a;
  padding: 24px;
  background: #fafafa;
}
h1 {
  font-size: 20px;
  margin-bottom: 16px;
}
.metadata {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 24px;
}
.metadata table {
  border-collapse: collapse;
}
.metadata td {
  padding: 2px 12px 2px 0;
  vertical-align: top;
}
.metadata td:first-child {
  font-weight: 600;
  white-space: nowrap;
}
.controls {
  margin-bottom: 16px;
}
.controls input {
  padding: 6px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
  width: 300px;
}
table.data {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}
table.data th {
  background: #f5f5f5;
  border-bottom: 2px solid #e0e0e0;
  padding: 8px 10px;
  text-align: left;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
table.data th:hover {
  background: #eaeaea;
}
table.data th .sort-arrow {
  margin-left: 4px;
  opacity: 0.4;
}
table.data th .sort-arrow.active {
  opacity: 1;
}
table.data td {
  padding: 6px 10px;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: middle;
}
table.data td.emoji-char {
  font-size: 24px;
  text-align: center;
  width: 50px;
}
table.data td.numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
tr.risk-red {
  background-color: #fee2e2;
}
tr.risk-yellow {
  background-color: #fef3c7;
}
.legend {
  margin-top: 16px;
  font-size: 12px;
  color: #666;
}
.legend span {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 1px solid #ccc;
  vertical-align: middle;
  margin-right: 4px;
}
.legend .swatch-red { background-color: #fee2e2; }
.legend .swatch-yellow { background-color: #fef3c7; }
"""

_JS = """\
(function() {
  "use strict";
  var table = document.querySelector("table.data");
  if (!table) return;
  var thead = table.querySelector("thead");
  var tbody = table.querySelector("tbody");
  var headers = thead.querySelectorAll("th");
  var filterInput = document.getElementById("filter-input");
  var currentSort = { col: -1, asc: true };

  function getCellValue(row, col) {
    var cell = row.children[col];
    return cell ? cell.textContent.trim() : "";
  }

  function compareValues(a, b, numeric) {
    if (numeric) {
      var na = parseFloat(a) || 0;
      var nb = parseFloat(b) || 0;
      return na - nb;
    }
    return a.localeCompare(b);
  }

  function sortTable(colIndex) {
    var rows = Array.from(tbody.querySelectorAll("tr"));
    var isNumeric = headers[colIndex].dataset.type === "numeric";
    var asc = (currentSort.col === colIndex) ? !currentSort.asc : true;
    currentSort = { col: colIndex, asc: asc };

    rows.sort(function(a, b) {
      var va = getCellValue(a, colIndex);
      var vb = getCellValue(b, colIndex);
      var result = compareValues(va, vb, isNumeric);
      return asc ? result : -result;
    });

    rows.forEach(function(row) { tbody.appendChild(row); });
    updateSortArrows(colIndex, asc);
  }

  function updateSortArrows(colIndex, asc) {
    headers.forEach(function(th, i) {
      var arrow = th.querySelector(".sort-arrow");
      if (!arrow) return;
      if (i === colIndex) {
        arrow.textContent = asc ? "\\u25B2" : "\\u25BC";
        arrow.classList.add("active");
      } else {
        arrow.textContent = "\\u25B2";
        arrow.classList.remove("active");
      }
    });
  }

  function filterRows(query) {
    var rows = tbody.querySelectorAll("tr");
    var lower = query.toLowerCase();
    rows.forEach(function(row) {
      var text = row.textContent.toLowerCase();
      row.style.display = text.indexOf(lower) >= 0 ? "" : "none";
    });
  }

  headers.forEach(function(th, i) {
    th.addEventListener("click", function() { sortTable(i); });
  });

  if (filterInput) {
    filterInput.addEventListener("input", function() {
      filterRows(this.value);
    });
  }
})();
"""


def generate_scan_report(
    findings: list[ScanFinding],
    context: ScanContext,
    out_path: Path,
) -> None:
    """Generate the scan report HTML file."""
    lines: list[str] = []
    _append_html_header(lines, "emojihunt scan report")
    _append_metadata_section(lines, context)

    # Controls
    lines.append('<div class="controls">')
    lines.append(
        '  <input type="text" id="filter-input" '
        'placeholder="Filter emojis..." autocomplete="off">'
    )
    lines.append("</div>")
    lines.append("")

    # Table
    columns = [
        ("Emoji", "text"),
        ("Risk", "text"),
        ("Reasons", "text"),
        ("Name", "text"),
        ("Code Points", "text"),
        ("Emoji Version", "numeric"),
        ("Presentation", "text"),
        ("ZWJ", "text"),
        ("Count", "numeric"),
    ]
    _append_table_header(lines, columns)
    lines.append("  <tbody>")

    # Sort: occurrence count desc, then code points asc
    sorted_findings = sorted(
        findings, key=lambda f: (-f.occurrence_count, f.metadata.code_points)
    )

    for finding in sorted_findings:
        m = finding.metadata
        css_class = _RISK_CSS_CLASSES.get(m.risk_level, "")
        class_attr = f' class="{css_class}"' if css_class else ""
        lines.append(f"    <tr{class_attr}>")
        lines.append(f'      <td class="emoji-char">{html.escape(m.char)}</td>')
        lines.append(f"      <td>{html.escape(m.risk_level.value)}</td>")
        lines.append(f"      <td>{html.escape('; '.join(m.risk_reasons))}</td>")
        lines.append(f"      <td>{html.escape(m.name)}</td>")
        lines.append(f"      <td>{html.escape(m.code_points)}</td>")
        lines.append(f"      <td class=\"numeric\">{html.escape(m.unicode_version)}</td>")
        lines.append(
            f"      <td>{_yes_no(m.emoji_presentation)}</td>"
        )
        lines.append(f"      <td>{_yes_no(m.is_zwj)}</td>")
        lines.append(
            f'      <td class="numeric">{finding.occurrence_count}</td>'
        )
        lines.append("    </tr>")

    lines.append("  </tbody>")
    lines.append("</table>")
    _append_legend(lines)
    _append_html_footer(lines)

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_catalog(
    emojis: list[EmojiMetadata],
    out_path: Path,
) -> None:
    """Generate the emoji catalog HTML file."""
    lines: list[str] = []
    _append_html_header(lines, "emojihunt emoji catalog")

    # Metadata
    lines.append('<div class="metadata">')
    lines.append("  <table>")
    lines.append("    <tr>")
    lines.append("      <td>Total emojis</td>")
    lines.append(f"      <td>{len(emojis)}</td>")
    lines.append("    </tr>")
    lines.append("  </table>")
    lines.append("</div>")
    lines.append("")

    # Controls
    lines.append('<div class="controls">')
    lines.append(
        '  <input type="text" id="filter-input" '
        'placeholder="Filter emojis..." autocomplete="off">'
    )
    lines.append("</div>")
    lines.append("")

    # Table — catalog has more columns than scan report
    columns = [
        ("Emoji", "text"),
        ("Risk", "text"),
        ("Reasons", "text"),
        ("Name", "text"),
        ("Code Points", "text"),
        ("Emoji Version", "numeric"),
        ("Presentation", "text"),
        ("ZWJ", "text"),
        ("Var. Selector", "text"),
        ("Skin Tone", "text"),
    ]
    _append_table_header(lines, columns)
    lines.append("  <tbody>")

    for m in emojis:
        css_class = _RISK_CSS_CLASSES.get(m.risk_level, "")
        class_attr = f' class="{css_class}"' if css_class else ""
        lines.append(f"    <tr{class_attr}>")
        lines.append(f'      <td class="emoji-char">{html.escape(m.char)}</td>')
        lines.append(f"      <td>{html.escape(m.risk_level.value)}</td>")
        lines.append(f"      <td>{html.escape('; '.join(m.risk_reasons))}</td>")
        lines.append(f"      <td>{html.escape(m.name)}</td>")
        lines.append(f"      <td>{html.escape(m.code_points)}</td>")
        lines.append(f"      <td class=\"numeric\">{html.escape(m.unicode_version)}</td>")
        lines.append(f"      <td>{_yes_no(m.emoji_presentation)}</td>")
        lines.append(f"      <td>{_yes_no(m.is_zwj)}</td>")
        lines.append(f"      <td>{_yes_no(m.has_variation_selector)}</td>")
        lines.append(f"      <td>{_yes_no(m.has_skin_tone_modifier)}</td>")
        lines.append("    </tr>")

    lines.append("  </tbody>")
    lines.append("</table>")
    _append_legend(lines)
    _append_html_footer(lines)

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_handled_paths_file(
    handled_paths: list[HandledPath],
    out_path: Path,
) -> None:
    """Generate the handled-path list as a plain text file.

    One path per line, sorted alphabetically. No header, no metadata.
    """
    sorted_paths = sorted(handled_paths, key=lambda p: p.path)
    content = "\n".join(p.format_line() for p in sorted_paths)
    if content:
        content += "\n"
    out_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _append_html_header(lines: list[str], title: str) -> None:
    """Append the HTML document header through opening body tag."""
    lines.append("<!DOCTYPE html>")
    lines.append('<html lang="en">')
    lines.append("<head>")
    lines.append('  <meta charset="utf-8">')
    lines.append(
        '  <meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    lines.append(f"  <title>{html.escape(title)}</title>")
    lines.append("  <style>")
    for css_line in _CSS.splitlines():
        lines.append(f"    {css_line}" if css_line.strip() else "")
    lines.append("  </style>")
    lines.append("</head>")
    lines.append("<body>")
    lines.append(f"<h1>{html.escape(title)}</h1>")
    lines.append("")


def _append_html_footer(lines: list[str]) -> None:
    """Append the closing body/html tags with embedded JavaScript."""
    lines.append("")
    lines.append("<script>")
    for js_line in _JS.splitlines():
        lines.append(js_line)
    lines.append("</script>")
    lines.append("</body>")
    lines.append("</html>")


def _append_metadata_section(lines: list[str], context: ScanContext) -> None:
    """Append the metadata block for a scan report."""
    lines.append('<div class="metadata">')
    lines.append("  <table>")

    metadata_rows = [
        ("Generated (UTC)", context.started_utc),
        ("Generated (local)", context.started_local),
        ("Duration", f"{context.duration_seconds:.2f}s"),
        ("Targets", ", ".join(context.targets)),
        ("Ignore file", context.ignore_file or "None"),
        ("Files scanned", str(context.files_scanned)),
        ("Files skipped", str(context.files_skipped)),
        ("Files errored", str(context.files_errored)),
        ("Unique emojis", str(context.unique_emojis_found)),
        ("Total occurrences", str(context.total_occurrences)),
    ]

    for label, value in metadata_rows:
        lines.append("    <tr>")
        lines.append(f"      <td>{html.escape(label)}</td>")
        lines.append(f"      <td>{html.escape(value)}</td>")
        lines.append("    </tr>")

    lines.append("  </table>")
    lines.append("</div>")
    lines.append("")


def _append_table_header(
    lines: list[str], columns: list[tuple[str, str]]
) -> None:
    """Append the table and thead with sortable column headers."""
    lines.append('<table class="data">')
    lines.append("  <thead>")
    lines.append("    <tr>")
    for col_name, col_type in columns:
        data_attr = f' data-type="{col_type}"' if col_type == "numeric" else ""
        lines.append(
            f"      <th{data_attr}>"
            f'{html.escape(col_name)}<span class="sort-arrow">\u25B2</span>'
            f"</th>"
        )
    lines.append("    </tr>")
    lines.append("  </thead>")


def _append_legend(lines: list[str]) -> None:
    """Append the color legend below the table."""
    lines.append('<div class="legend">')
    lines.append(
        '  <span class="swatch-red"></span> RED: unpredictable rendering '
        "(variation selector or text-default presentation) &nbsp;&nbsp;"
    )
    lines.append(
        '  <span class="swatch-yellow"></span> YELLOW: fragmentation risk '
        "(ZWJ, skin tone, or recent emoji version)"
    )
    lines.append("</div>")


def _yes_no(value: bool) -> str:
    """Format a boolean as Yes/No for table cells."""
    return "Yes" if value else "No"
