"""Web page fetching and saving utilities."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx

from .html_parser import decode_html_bytes, extract_html_title


def build_unique_page_path(
    pages_path: Path,
    *,
    timestamp: str,
    citation_number: int,
    unique_fragment: str | None = None,
) -> Path:
    """Build a unique destination path for a citation HTML page."""
    fragment = unique_fragment or datetime.now().strftime("%f")
    stem = f"{timestamp}_{citation_number:02d}_{fragment}"
    filepath = pages_path / f"{stem}.html"

    # Last-resort collision loop: preserve readability while ensuring uniqueness.
    counter = 1
    while filepath.exists():
        if counter <= 9:
            suffix = str(counter)
        else:
            suffix = uuid4().hex[:8]
        filepath = pages_path / f"{stem}_{suffix}.html"
        counter += 1
    return filepath


async def fetch_page_title(url: str, timeout_sec: float = 5.0) -> str | None:
    """Fetch a page and extract its title.

    Args:
        url: URL to fetch
        timeout_sec: Request timeout in seconds

    Returns:
        Page title or None on failure
    """
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
        decoded = decode_html_bytes(resp.content, content_type)
        return extract_html_title(decoded)


async def fetch_and_save_page(
    url: str,
    pages_dir: str,
    citation_number: int,
    timestamp: str,
    timeout_sec: float = 5.0
) -> tuple[str | None, str | None]:
    """Fetch page, save to disk, and extract title.

    Args:
        url: URL to fetch
        pages_dir: Directory to save pages
        citation_number: Citation number (1-based)
        timestamp: Timestamp string (YYYY-MM-DD_HH-MM-SS)
        timeout_sec: Request timeout

    Returns:
        Tuple of (title, saved_filepath) or (None, None) on failure
    """
    timeout = httpx.Timeout(connect=3.0, read=timeout_sec, write=3.0, pool=3.0)
    headers = {
        "User-Agent": "poly-chat/1.0 (+citation-saver)",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").lower()
            if "html" not in content_type:
                return None, None

            # Decode HTML
            decoded = decode_html_bytes(resp.content, content_type)

            # Extract title
            title = extract_html_title(decoded)

            # Save to disk
            pages_path = Path(pages_dir)
            pages_path.mkdir(parents=True, exist_ok=True)

            filepath = build_unique_page_path(
                pages_path,
                timestamp=timestamp,
                citation_number=citation_number,
            )

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(decoded)

            return title, str(filepath)
    except Exception:
        return None, None
