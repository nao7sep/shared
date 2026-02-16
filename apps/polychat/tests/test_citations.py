"""Tests for citation normalization."""

import pytest

from poly_chat import citations as citation_utils


def test_normalize_citations_orders_keys_numbers_and_dedupes():
    citations = [
        {"url": "https://example.com/path", "title": "Example"},
        {"url": "https://example.com/path", "title": "Example"},
        {"url": "https://example.com/path#frag", "title": "Example"},
    ]
    result = citation_utils.normalize_citations(citations)
    assert result == [{"number": 1, "title": "Example", "url": "https://example.com/path"}]


def test_normalize_citations_sets_missing_or_invalid_values_to_none():
    citations = [
        {"url": "notaurl", "title": "x"},
        {"url": "https://example.com/a", "title": ""},
        {"url": "https://example.com/b", "title": "2"},
        {"title": "no-url"},
    ]
    result = citation_utils.normalize_citations(citations)
    assert result == [
        {"number": 1, "title": "x", "url": None},
        {"number": 2, "title": None, "url": "https://example.com/a"},
        {"number": 3, "title": None, "url": "https://example.com/b"},
        {"number": 4, "title": "no-url", "url": None},
    ]


def test_normalize_citations_drops_host_like_title_when_in_url():
    citations = [
        {
            "title": "nodewave.io",
            "url": "https://www.nodewave.io/blog/top-ai-models-2026-guide-compare-choose-deploy",
        }
    ]
    result = citation_utils.normalize_citations(citations)
    assert result == [
        {
            "number": 1,
            "title": None,
            "url": "https://www.nodewave.io/blog/top-ai-models-2026-guide-compare-choose-deploy",
        }
    ]


def test_normalize_citations_keeps_vertex_redirect_url_for_later_resolution():
    citations = [
        {
            "url": (
                "https://vertexaisearch.cloud.google.com/grounding-api-redirect/"
                "?url=https%3A%2F%2Fexample.com%2Fresearch"
            ),
            "title": "Research",
        }
    ]
    result = citation_utils.normalize_citations(citations)
    assert result == [
        {
            "number": 1,
            "title": "Research",
            "url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/?url=https%3A%2F%2Fexample.com%2Fresearch",
        }
    ]


@pytest.mark.asyncio
async def test_resolve_vertex_citation_urls_prefers_http_resolution(monkeypatch):
    async def fake_http(client, url):
        return "https://example.com/final"

    monkeypatch.setattr(citation_utils, "_resolve_vertex_via_http", fake_http)

    citations = citation_utils.normalize_citations(
        [{"url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/opaque", "title": "Final"}]
    )
    result = await citation_utils.resolve_vertex_citation_urls(citations)
    assert result == [{"number": 1, "title": "Final", "url": "https://example.com/final"}]


@pytest.mark.asyncio
async def test_resolve_vertex_citation_urls_sets_unresolved_vertex_url_to_none(monkeypatch):
    async def fake_http(client, url):
        return None

    monkeypatch.setattr(citation_utils, "_resolve_vertex_via_http", fake_http)

    citations = citation_utils.normalize_citations(
        [{"url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/opaque", "title": "Final"}]
    )
    result = await citation_utils.resolve_vertex_citation_urls(citations)
    assert result == [{"number": 1, "title": "Final", "url": None}]


@pytest.mark.asyncio
async def test_resolve_vertex_citation_urls_drops_host_like_title_after_resolution(monkeypatch):
    async def fake_http(client, url):
        return "https://www.nodewave.io/blog/top-ai-models-2026-guide-compare-choose-deploy"

    monkeypatch.setattr(citation_utils, "_resolve_vertex_via_http", fake_http)

    citations = citation_utils.normalize_citations(
        [
            {
                "url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/opaque",
                "title": "nodewave.io",
            }
        ]
    )
    result = await citation_utils.resolve_vertex_citation_urls(citations)
    assert result == [
        {
            "number": 1,
            "title": None,
            "url": "https://www.nodewave.io/blog/top-ai-models-2026-guide-compare-choose-deploy",
        }
    ]
