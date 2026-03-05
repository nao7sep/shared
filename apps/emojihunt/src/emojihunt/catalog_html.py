"""Generate the full emoji catalog as HTML."""

import html

from .models import EmojiEntry, RiskLevel

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
]


def generate_catalog_html(entries: list[EmojiEntry]) -> str:
    """Generate the full catalog HTML sorted by canonical code point sequence."""
    sorted_entries = sorted(entries, key=lambda e: e.sort_key_code_points)

    rows: list[str] = []
    for entry in sorted_entries:
        rows.append(_render_row(entry))

    return _wrap_html(
        title="Emojihunt Catalog",
        headers=_HEADERS,
        rows="\n".join(rows),
    )


def _render_row(entry: EmojiEntry) -> str:
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
</tr>"""


def _row_class(level: RiskLevel) -> str:
    if level == RiskLevel.RED:
        return "risk-red"
    if level == RiskLevel.YELLOW:
        return "risk-yellow"
    return "risk-none"


def _wrap_html(title: str, headers: list[str], rows: str) -> str:
    header_cells = "\n".join(f"      <th>{h}</th>" for h in headers)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      margin: 2em;
    }}
    h1 {{
      margin-bottom: 1em;
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
