"""Citation normalization and title enrichment helpers."""

from __future__ import annotations

import asyncio
import html
import re
from urllib.parse import parse_qs, urlparse

import httpx

try:
    from charset_normalizer import from_bytes as detect_charset_from_bytes
except Exception:  # pragma: no cover - optional dependency via transitive install
    detect_charset_from_bytes = None


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


def _extract_redirect_target(url: str) -> str:
    """Resolve known redirect wrappers to their target URL when present."""
    try:
        parsed = urlparse(url)
    except Exception:
        return url

    host = (parsed.netloc or "").lower()
    if "vertexaisearch.cloud.google.com" not in host:
        return url

    query = parse_qs(parsed.query)
    for key in ("url", "q", "target", "target_url", "redirect_url"):
        values = query.get(key)
        if values and values[0]:
            return values[0]
    return url


def _normalized_url_key(url: str) -> str:
    """Build a dedupe key for URLs while preserving original URL output."""
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl().rstrip("/")


def _is_valid_http_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_numeric_title(value: str | None) -> bool:
    if not value or not isinstance(value, str):
        return False
    return _NUMERIC_TITLE_RE.match(value) is not None


def _is_domain_like_title(value: str | None, url: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    if host.startswith("www."):
        host = host[4:]
    title = value.strip().lower()
    return bool(host) and title in {host, host.split(":")[0]}


def _needs_title_enrichment(title: str | None, url: str) -> bool:
    if title is None:
        return True
    stripped = title.strip()
    if not stripped:
        return True
    if _is_numeric_title(stripped):
        return True
    if _is_domain_like_title(stripped, url):
        return True
    return False


def normalize_citations(citations: object) -> list[dict[str, object]]:
    """Normalize citation shape, key order, numbering, and deduplicate.

    Output dict key order is: number, title, url.
    """
    if not isinstance(citations, list):
        return []

    normalized: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    for item in citations:
        if not isinstance(item, dict):
            continue
        raw_url = item.get("url")
        raw_title = item.get("title")
        if not isinstance(raw_url, str) or not raw_url.strip():
            continue

        resolved_url = _extract_redirect_target(raw_url.strip())
        if not _is_valid_http_url(resolved_url):
            continue

        title = raw_title.strip() if isinstance(raw_title, str) and raw_title.strip() else None
        key = (_normalized_url_key(resolved_url).lower(), (title or "").lower())
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"title": title, "url": resolved_url})

    for i, citation in enumerate(normalized, 1):
        citation["number"] = i

    # Preserve key order for json output readability.
    return [
        {
            "number": c["number"],
            "title": c.get("title"),
            "url": c["url"],
        }
        for c in normalized
    ]


def citations_need_enrichment(citations: list[dict[str, object]]) -> bool:
    """Return True if any citation title appears missing/low quality."""
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        url = citation.get("url")
        title = citation.get("title")
        if isinstance(url, str) and _is_valid_http_url(url):
            if _needs_title_enrichment(title if isinstance(title, str) else None, url):
                return True
    return False


def _extract_html_title(raw_html: str) -> str | None:
    match = _TITLE_RE.search(raw_html)
    if not match:
        return None
    value = html.unescape(match.group(1))
    value = " ".join(value.split()).strip()
    return value or None


def _extract_charset_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    match = re.search(r"charset\s*=\s*([a-zA-Z0-9_\-]+)", content_type, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _extract_charset_from_meta(raw_bytes: bytes) -> str | None:
    head = raw_bytes[:8192]
    for pattern in (_META_CHARSET_RE, _META_HTTP_EQUIV_RE):
        match = pattern.search(head)
        if match:
            try:
                return match.group(1).decode("ascii", errors="ignore").strip()
            except Exception:
                continue
    return None


def _extract_charset_from_xml_decl(raw_bytes: bytes) -> str | None:
    head = raw_bytes[:2048]
    match = _XML_DECL_ENCODING_RE.search(head)
    if not match:
        return None
    try:
        return match.group(1).decode("ascii", errors="ignore").strip()
    except Exception:
        return None


def _decode_html_bytes(raw_bytes: bytes, content_type: str | None) -> str:
    candidates: list[str] = []
    header_charset = _extract_charset_from_content_type(content_type)
    meta_charset = _extract_charset_from_meta(raw_bytes)
    xml_charset = _extract_charset_from_xml_decl(raw_bytes)

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


async def _fetch_page_title(url: str, timeout_sec: float = 5.0) -> str | None:
    timeout = httpx.Timeout(connect=3.0, read=timeout_sec, write=3.0, pool=3.0)
    headers = {
        "User-Agent": "poly-chat/1.0 (+citation-title-enricher)",
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = (resp.headers.get("content-type") or "").lower()
        if "html" not in content_type:
            return None
        decoded = _decode_html_bytes(resp.content, content_type)
        return _extract_html_title(decoded)


async def enrich_citation_titles(
    citations: list[dict[str, object]],
    *,
    concurrency: int = 3,
) -> tuple[list[dict[str, object]], bool]:
    """Best-effort async title enrichment for low-quality/missing titles.

    Returns:
        (updated_citations, changed)
    """
    if not citations:
        return citations, False

    updated = [dict(c) for c in citations]
    initial_all_numeric = all(
        _is_numeric_title(c.get("title") if isinstance(c.get("title"), str) else None)
        for c in updated
        if isinstance(c, dict)
    )

    sem = asyncio.Semaphore(max(1, concurrency))
    successful_fetches = 0
    changed = False

    async def enrich_one(index: int, citation: dict[str, object]) -> None:
        nonlocal successful_fetches, changed
        url = citation.get("url")
        title = citation.get("title")
        if not isinstance(url, str) or not _is_valid_http_url(url):
            return
        existing_title = title if isinstance(title, str) else None
        if not _needs_title_enrichment(existing_title, url):
            return
        try:
            async with sem:
                fetched = await _fetch_page_title(url)
        except Exception:
            return
        if fetched:
            successful_fetches += 1
            if fetched != existing_title:
                updated[index]["title"] = fetched
                changed = True

    await asyncio.gather(
        *(enrich_one(i, c) for i, c in enumerate(updated) if isinstance(c, dict))
    )

    # If provider supplied only numeric placeholders and no enrichment succeeded,
    # keep URLs and drop unusable numeric titles.
    if initial_all_numeric and successful_fetches == 0:
        for c in updated:
            if isinstance(c.get("title"), str):
                c["title"] = None
                changed = True

    # Rebuild numbering deterministically.
    for i, c in enumerate(updated, 1):
        c["number"] = i
    reordered = [{"number": c.get("number"), "title": c.get("title"), "url": c.get("url")} for c in updated]
    return reordered, changed
