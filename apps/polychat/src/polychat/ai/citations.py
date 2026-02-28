"""Citation normalization helpers."""

from __future__ import annotations

import asyncio
import re
from urllib.parse import urljoin, urlparse

import httpx
from .types import Citation
from ..timeouts import (
    CITATION_REDIRECT_RESOLVE_CONCURRENCY,
    CITATION_REDIRECT_RESOLVE_TIMEOUT_SEC,
)

_NUMERIC_TITLE_RE = re.compile(r"^\s*\d+\s*$")
_HOST_LIKE_TITLE_RE = re.compile(r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$")
_VERTEX_HOST_SUFFIX = "vertexaisearch.cloud.google.com"
_VERTEX_PATH_HINT = "grounding-api-redirect"


def _normalized_url_key(url: str | None) -> str | None:
    """Build a dedupe key for URLs while preserving original URL output."""
    if not url:
        return None
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


def _clean_title(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    title = value.strip()
    if not title:
        return None
    # Providers sometimes return numeric placeholders (e.g. "1", "2").
    if _NUMERIC_TITLE_RE.match(title):
        return None
    return title


def _normalize_host(host: str | None) -> str | None:
    if not host:
        return None
    normalized = host.strip().lower()
    if normalized.startswith("www."):
        normalized = normalized[4:]
    if ":" in normalized:
        normalized = normalized.split(":", 1)[0]
    if not normalized:
        return None
    return normalized


def _domain_like_title(title: str | None) -> str | None:
    if not title:
        return None
    candidate = title.strip().lower().rstrip("/")
    if not candidate:
        return None
    if candidate.startswith("http://") or candidate.startswith("https://"):
        candidate = urlparse(candidate).netloc.lower()
    normalized_candidate = _normalize_host(candidate)
    if not normalized_candidate:
        return None
    if not _HOST_LIKE_TITLE_RE.fullmatch(normalized_candidate):
        return None
    return normalized_candidate


def _is_host_like_title_for_url(title: str | None, url: str | None) -> bool:
    if not title or not url:
        return False
    if not _is_valid_http_url(url):
        return False

    candidate = _domain_like_title(title)
    if not candidate:
        return False

    parsed = urlparse(url)
    host = _normalize_host(parsed.netloc)
    if not host:
        return False

    if candidate == host:
        return True
    if host.endswith(f".{candidate}"):
        return True
    if candidate.endswith(f".{host}"):
        return True
    return False


def _looks_like_vertex_redirect(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    return host.endswith(_VERTEX_HOST_SUFFIX) or _VERTEX_PATH_HINT in path


def _clean_url(raw_url: object) -> str | None:
    if not isinstance(raw_url, str):
        return None
    url = raw_url.strip()
    if not url:
        return None
    return url if _is_valid_http_url(url) else None


def _dedupe_and_number(citations: list[Citation]) -> list[Citation]:
    deduped: list[Citation] = []
    seen: set[tuple[str | None, str | None]] = set()

    for citation in citations:
        raw_url = citation.get("url")
        raw_title = citation.get("title")
        url = raw_url if isinstance(raw_url, str) else None
        title = raw_title if isinstance(raw_title, str) else None
        if _is_host_like_title_for_url(title, url):
            title = None
        normalized_key = _normalized_url_key(url)
        key = (
            normalized_key.lower() if isinstance(normalized_key, str) else None,
            title.lower() if isinstance(title, str) else None,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "number": len(deduped) + 1,
                "title": title,
                "url": url,
            }
        )

    return deduped


def normalize_citations(citations: object) -> list[Citation]:
    """Normalize citation shape, numbering, and deduplicate.

    Output key order is: number, title, url.
    """
    if not isinstance(citations, list):
        return []

    normalized: list[Citation] = []
    for item in citations:
        if isinstance(item, dict):
            raw_url = item.get("url", item.get("uri"))
            raw_title = item.get("title")
            normalized.append(
                {
                    "title": _clean_title(raw_title),
                    "url": _clean_url(raw_url),
                }
            )
        elif isinstance(item, str):
            normalized.append(
                {
                    "title": None,
                    "url": _clean_url(item),
                }
            )

    return _dedupe_and_number(normalized)


def _extract_location_header(response: httpx.Response) -> str | None:
    location = response.headers.get("location")
    if not location:
        return None
    candidate = location.strip()
    if not candidate:
        return None
    # Handle relative redirect locations.
    absolute = urljoin(str(response.request.url), candidate)
    return absolute if _is_valid_http_url(absolute) else None


async def _resolve_vertex_via_http(client: httpx.AsyncClient, url: str) -> str | None:
    # GET first: vertex redirect endpoints commonly provide Location on GET.
    for method in ("GET", "HEAD"):
        try:
            response = await client.request(method, url, follow_redirects=False)
        except Exception:
            continue
        resolved = _extract_location_header(response)
        if resolved:
            return resolved
    return None


async def resolve_vertex_citation_urls(
    citations: list[Citation],
    *,
    timeout_sec: float = CITATION_REDIRECT_RESOLVE_TIMEOUT_SEC,
    concurrency: int = CITATION_REDIRECT_RESOLVE_CONCURRENCY,
) -> list[Citation]:
    """Resolve vertex redirect URLs to destination URLs via HTTP redirect headers.

    Vertex URLs contain base64-encoded data and require an HTTP request
    to resolve to the actual destination URL.
    """
    if not citations:
        return citations

    updated: list[Citation] = []
    for c in citations:
        copied: Citation = {"title": c.get("title"), "url": c.get("url")}
        number = c.get("number")
        if isinstance(number, int):
            copied["number"] = number
        updated.append(copied)
    timeout = httpx.Timeout(timeout_sec)
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async with httpx.AsyncClient(timeout=timeout) as client:

        async def resolve_one(index: int, citation: Citation) -> None:
            url = citation.get("url")
            if not isinstance(url, str) or not _is_valid_http_url(url):
                return
            if not _looks_like_vertex_redirect(url):
                return

            async with semaphore:
                resolved = await _resolve_vertex_via_http(client, url)

            # If unresolved, vertex URL is considered unusable for history/citations.
            updated[index]["url"] = resolved if _is_valid_http_url(resolved) else None

        await asyncio.gather(
            *(resolve_one(i, c) for i, c in enumerate(updated) if isinstance(c, dict))
        )

    return _dedupe_and_number(updated)
