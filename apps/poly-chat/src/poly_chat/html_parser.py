"""HTML parsing and encoding detection utilities."""

from __future__ import annotations

import html
import re

try:
    from charset_normalizer import from_bytes as detect_charset_from_bytes
except Exception:  # pragma: no cover - optional dependency via transitive install
    detect_charset_from_bytes = None


# Regex patterns for parsing HTML and encoding information
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", flags=re.IGNORECASE | re.DOTALL)
_NUMERIC_TITLE_RE = re.compile(r"^\s*\d+\s*$")
_META_CHARSET_RE = re.compile(
    rb"<meta[^>]+charset\s*=\s*['\"]?\s*([a-zA-Z0-9_\-]+)\s*['\"]?",
    flags=re.IGNORECASE,
)
_META_HTTP_EQUIV_RE = re.compile(
    rb"<meta[^>]+http-equiv\s*=\s*['\"]content-type['\"][^>]*content\s*=\s*['\"][^\"'>]*charset\s*=\s*([a-zA-Z0-9_\-]+)[^\"'>]*['\"]",
    flags=re.IGNORECASE,
)
_XML_DECL_ENCODING_RE = re.compile(
    rb"<\?xml[^>]*encoding\s*=\s*['\"]\s*([a-zA-Z0-9_\-]+)\s*['\"][^>]*\?>",
    flags=re.IGNORECASE,
)


def extract_charset_from_content_type(content_type: str) -> str | None:
    """Extract charset from HTTP Content-Type header.

    Args:
        content_type: Content-Type header value

    Returns:
        Charset name or None
    """
    if not content_type:
        return None
    parts = content_type.lower().split(";")
    for part in parts:
        part = part.strip()
        if part.startswith("charset="):
            charset = part[8:].strip().strip('"').strip("'")
            return charset if charset else None
    return None


def extract_charset_from_meta(raw_bytes: bytes) -> str | None:
    """Extract charset from HTML meta tags.

    Args:
        raw_bytes: Raw HTML bytes

    Returns:
        Charset name or None
    """
    match = _META_CHARSET_RE.search(raw_bytes)
    if match:
        return match.group(1).decode("ascii", errors="ignore")
    match = _META_HTTP_EQUIV_RE.search(raw_bytes)
    if match:
        return match.group(1).decode("ascii", errors="ignore")
    return None


def extract_charset_from_xml_decl(raw_bytes: bytes) -> str | None:
    """Extract encoding from XML declaration.

    Args:
        raw_bytes: Raw HTML/XML bytes

    Returns:
        Encoding name or None
    """
    match = _XML_DECL_ENCODING_RE.search(raw_bytes[:1024])
    if match:
        return match.group(1).decode("ascii", errors="ignore")
    return None


def decode_html_bytes(raw_bytes: bytes, content_type: str = "") -> str:
    """Decode HTML bytes with multi-stage fallback.

    Priority order:
    1. HTTP Content-Type header charset
    2. HTML meta tag charset
    3. XML declaration encoding
    4. charset_normalizer detection (if available)
    5. Common Japanese/Unicode encodings
    6. UTF-8 with error replacement

    Args:
        raw_bytes: Raw HTML bytes
        content_type: HTTP Content-Type header value

    Returns:
        Decoded HTML string
    """
    candidates: list[str] = []
    header_charset = extract_charset_from_content_type(content_type)
    meta_charset = extract_charset_from_meta(raw_bytes)
    xml_charset = extract_charset_from_xml_decl(raw_bytes)

    # User preference: meta-declared encoding before XML declaration.
    # HTTP header stays first because it's transport-level metadata.
    for item in (header_charset, meta_charset, xml_charset):
        if item and item.lower() not in {c.lower() for c in candidates}:
            candidates.append(item)

    if detect_charset_from_bytes is not None:
        try:
            detected = detect_charset_from_bytes(raw_bytes).best()
            encoding = getattr(detected, "encoding", None)
            if isinstance(encoding, str) and encoding.lower() not in {c.lower() for c in candidates}:
                candidates.append(encoding)
        except Exception:
            pass

    candidates.extend(["utf-8", "cp932", "shift_jis", "euc-jp", "iso-2022-jp"])
    tried: set[str] = set()
    for enc in candidates:
        enc_key = enc.lower()
        if enc_key in tried:
            continue
        tried.add(enc_key)
        try:
            return raw_bytes.decode(enc)
        except Exception:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def extract_html_title(html_text: str) -> str | None:
    """Extract title from HTML string.

    Args:
        html_text: Decoded HTML string

    Returns:
        Title text or None
    """
    match = _TITLE_RE.search(html_text)
    if not match:
        return None
    title = match.group(1).strip()
    # Decode HTML entities
    title = html.unescape(title)
    # Normalize whitespace
    title = " ".join(title.split())
    return title if title else None
