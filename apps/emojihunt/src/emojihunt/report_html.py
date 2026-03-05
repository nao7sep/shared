"""Generate the timestamped findings report as HTML."""

import html
from datetime import datetime

from .models import RiskLevel, ScanFinding

_HEADERS = [
    "Emoji",
    "Name",
    "Code Points",
    "Unicode Version",
    "Presentation",
    "Variation Selector",
    "Zero Width Joiner",
    "Skin Tone Modifier",
    "Risk Level",
    "Risk Reasons",
    "Group",
    "Subgroup",
    "Occurrences",
]


def generate_report_html(
    findings: list[ScanFinding],
    *,
    generated_at_local: datetime,
    generated_at_utc: datetime,
) -> str:
    """Generate the findings report HTML sorted by risk, count, then code points."""
    sorted_findings = sorted(findings, key=lambda f: f.sort_key)

    rows: list[str] = []
    for finding in sorted_findings:
        rows.append(_render_row(finding))

    local_str = generated_at_local.strftime("%Y-%m-%d %H:%M:%S")
    utc_str = generated_at_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    return _wrap_html(
        title="Emojihunt Findings Report",
        subtitle=f"Generated: {local_str}",
        utc_timestamp=utc_str,
        headers=_HEADERS,
        rows="\n".join(rows),
        total_findings=len(findings),
        total_occurrences=sum(f.count for f in findings),
    )


def _render_row(finding: ScanFinding) -> str:
    entry = finding.entry
    cls = _row_class(entry.risk_level)
    presentation = "text-default" if entry.is_text_default else "emoji-default"
    return f"""<tr class="{cls}">
  <td class="emoji">{html.escape(entry.sequence)}</td>
  <td class="name">{html.escape(entry.name)}</td>
  <td class="code-points">{html.escape(entry.code_points)}</td>
  <td class="unicode-version">{html.escape(entry.unicode_version)}</td>
  <td class="presentation">{presentation}</td>
  <td class="variation-selector">{"yes" if entry.has_variation_selector else "no"}</td>
  <td class="zwj">{"yes" if entry.has_zwj else "no"}</td>
  <td class="skin-tone">{"yes" if entry.has_skin_tone_modifier else "no"}</td>
  <td class="risk-level">{entry.risk_level.value}</td>
  <td class="risk-reasons">{html.escape(", ".join(entry.risk_reasons))}</td>
  <td class="group">{html.escape(entry.group)}</td>
  <td class="subgroup">{html.escape(entry.subgroup)}</td>
  <td class="occurrence-count">{finding.count}</td>
</tr>"""


def _row_class(level: RiskLevel) -> str:
    if level == RiskLevel.RED:
        return "risk-red"
    if level == RiskLevel.YELLOW:
        return "risk-yellow"
    return "risk-none"


def _wrap_html(
    title: str,
    subtitle: str,
    utc_timestamp: str,
    headers: list[str],
    rows: str,
    total_findings: int,
    total_occurrences: int,
) -> str:
    header_cells = "\n".join(f"      <th>{h}</th>" for h in headers)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="generated-utc" content="{html.escape(utc_timestamp)}">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      margin: 2em;
    }}
    h1 {{
      margin-bottom: 0.2em;
    }}
    .subtitle {{
      color: #666;
      margin-bottom: 1em;
    }}
    .summary {{
      margin-bottom: 1.5em;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
    }}
    th, td {{
      border: 1px solid #ccc;
      padding: 0.4em 0.6em;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #f5f5f5;
      position: sticky;
      top: 0;
    }}
    .emoji {{
      font-size: 1.4em;
    }}
    .code-points {{
      font-family: monospace;
    }}
    tr.risk-red {{
      background-color: #fdd;
    }}
    tr.risk-yellow {{
      background-color: #ffd;
    }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p class="subtitle">{html.escape(subtitle)}</p>
  <div class="summary">
    <p>Unique sequences: {total_findings}</p>
    <p>Total occurrences: {total_occurrences}</p>
  </div>
  <table>
    <thead>
      <tr>
{header_cells}
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>
"""
