"""Citation normalization and title enrichment helpers."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from urllib.parse import urlparse

from .page_fetcher import fetch_and_save_page, fetch_page_title
from .timeouts import PAGE_FETCH_DEFAULT_READ_TIMEOUT_SEC


_NUMERIC_TITLE_RE = re.compile(r"^\s*\d+\s*$")


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

        url = raw_url.strip()
        if not _is_valid_http_url(url):
            continue

        title = raw_title.strip() if isinstance(raw_title, str) and raw_title.strip() else None
        key = (_normalized_url_key(url).lower(), (title or "").lower())
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"title": title, "url": url})

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


async def enrich_citation_titles(
    citations: list[dict[str, object]],
    *,
    concurrency: int = 3,
    pages_dir: str | None = None,
    timeout_sec: float = PAGE_FETCH_DEFAULT_READ_TIMEOUT_SEC,
) -> tuple[list[dict[str, object]], bool]:
    """Best-effort async title enrichment for low-quality/missing titles.

    When pages_dir is provided, ALL citations are downloaded and saved to disk.
    Titles are extracted from the saved pages.

    Args:
        citations: List of citation dicts with url and title
        concurrency: Max concurrent downloads
        pages_dir: Optional directory to save all cited pages

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

    # Generate timestamp once for all citations in this batch
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    async def enrich_one(index: int, citation: dict[str, object]) -> None:
        nonlocal successful_fetches, changed
        url = citation.get("url")
        title = citation.get("title")
        if not isinstance(url, str) or not _is_valid_http_url(url):
            return
        existing_title = title if isinstance(title, str) else None

        # When pages_dir is provided, ALWAYS download and save pages
        if pages_dir:
            try:
                async with sem:
                    citation_number = citation.get("number", index + 1)
                    fetched_title, saved_path = await fetch_and_save_page(
                        url,
                        pages_dir,
                        citation_number,
                        timestamp,
                        timeout_sec=timeout_sec,
                    )
                if fetched_title:
                    successful_fetches += 1
                    if fetched_title != existing_title:
                        updated[index]["title"] = fetched_title
                        changed = True
            except Exception:
                return
        else:
            # Legacy behavior: only enrich when needed
            if not _needs_title_enrichment(existing_title, url):
                return
            try:
                async with sem:
                    fetched = await fetch_page_title(url, timeout_sec=timeout_sec)
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
