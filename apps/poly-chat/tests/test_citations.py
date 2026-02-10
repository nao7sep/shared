"""Tests for citation normalization and enrichment."""

import pytest

from poly_chat import citations as citation_utils
from poly_chat import page_fetcher
from poly_chat import html_parser


def test_normalize_citations_orders_keys_numbers_and_dedupes():
    citations = [
        {"url": "https://example.com/path", "title": "Example"},
        {"url": "https://example.com/path", "title": "Example"},
        {"url": "https://example.com/path#frag", "title": "Example"},
    ]
    result = citation_utils.normalize_citations(citations)
    assert result == [{"number": 1, "title": "Example", "url": "https://example.com/path"}]


def test_citations_need_enrichment_true_for_numeric_or_missing_titles():
    assert citation_utils.citations_need_enrichment(
        [{"number": 1, "title": "1", "url": "https://example.com"}]
    )
    assert citation_utils.citations_need_enrichment(
        [{"number": 1, "title": None, "url": "https://example.com"}]
    )


def test_citations_need_enrichment_false_for_real_title():
    assert not citation_utils.citations_need_enrichment(
        [{"number": 1, "title": "Meaningful Title", "url": "https://example.com"}]
    )


@pytest.mark.asyncio
async def test_enrich_citation_titles_updates_low_quality(monkeypatch):
    async def fake_fetch(url: str, timeout_sec: float = 5.0) -> str | None:
        return "Real Page Title"

    monkeypatch.setattr("poly_chat.citations.fetch_page_title", fake_fetch)
    citations = [{"number": 1, "title": "1", "url": "https://example.com/a"}]
    enriched, changed = await citation_utils.enrich_citation_titles(citations)
    assert changed is True
    assert enriched == [{"number": 1, "title": "Real Page Title", "url": "https://example.com/a"}]


@pytest.mark.asyncio
async def test_enrich_citation_titles_drops_numeric_when_fetch_fails(monkeypatch):
    async def fake_fetch(url: str, timeout_sec: float = 5.0) -> str | None:
        return None

    monkeypatch.setattr("poly_chat.citations.fetch_page_title", fake_fetch)
    citations = [
        {"number": 1, "title": "1", "url": "https://example.com/a"},
        {"number": 2, "title": "2", "url": "https://example.com/b"},
    ]
    enriched, changed = await citation_utils.enrich_citation_titles(citations)
    assert changed is True
    assert enriched == [
        {"number": 1, "title": None, "url": "https://example.com/a"},
        {"number": 2, "title": None, "url": "https://example.com/b"},
    ]


def test_decode_html_bytes_prefers_meta_over_xml():
    # XML declaration says euc-jp, meta says utf-8: meta should win.
    html_text = (
        '<?xml version="1.0" encoding="EUC-JP"?>'
        '<html><head><meta charset="utf-8"><title>日本語タイトル</title></head></html>'
    )
    raw = html_text.encode("utf-8")
    decoded = html_parser.decode_html_bytes(raw, "text/html")
    assert "日本語タイトル" in decoded


def test_decode_html_bytes_supports_shift_jis_with_meta():
    html_text = '<html><head><meta charset="Shift_JIS"><title>日本語サイト</title></head></html>'
    raw = html_text.encode("shift_jis")
    decoded = html_parser.decode_html_bytes(raw, "text/html")
    assert "日本語サイト" in decoded


def test_build_unique_page_path_avoids_same_timestamp_collisions(tmp_path):
    pages_path = tmp_path / "pages"
    pages_path.mkdir(parents=True, exist_ok=True)

    first = page_fetcher.build_unique_page_path(
        pages_path,
        timestamp="2026-02-10_12-34-56",
        citation_number=1,
        unique_fragment="123456",
    )
    first.write_text("<html>first</html>", encoding="utf-8")

    second = page_fetcher.build_unique_page_path(
        pages_path,
        timestamp="2026-02-10_12-34-56",
        citation_number=1,
        unique_fragment="123456",
    )

    assert first != second
    assert second.name.startswith("2026-02-10_12-34-56_01_123456")
    assert second.suffix == ".html"
