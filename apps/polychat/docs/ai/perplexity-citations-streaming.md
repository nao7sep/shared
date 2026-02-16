# Perplexity API: Citations in Streaming Responses

**Date:** February 10, 2026
**Issue:** Citations not displaying from Perplexity streaming responses
**Status:** Resolved

## Problem Summary

When using Perplexity's streaming API (with `stream=True`), citations were not being extracted and displayed to users, despite Perplexity including citation information in the response. Users would see citation markers like `[1]`, `[2]` embedded in the text but no "Sources:" section at the end.

## Root Cause

The issue was in **how we were extracting citations from streaming chunks**. The original code in `perplexity_provider.py` only looked for citations in chunks **without choices**:

```python
# OLD CODE - Only checked chunks without choices
if not chunk.choices:
    citations = self._extract_citations(chunk)
    # ...
```

However, Perplexity's API puts citations in the **final chunk that HAS choices** and a `finish_reason='stop'`.

## Discovery Process

### Test Script Results

A test script making a direct Perplexity API call revealed:

```python
# Final chunk (245) with finish_reason='stop'
chunk.choices[0].finish_reason = 'stop'
chunk.citations = [
    'https://www.weather25.com/...',
    'https://www.agatetravel.com/...',
    # ... 7 citations total
]
chunk.search_results = [
    {
        'title': 'Tokyo weather in February 2026 - Weather25.com',
        'url': 'https://www.weather25.com/...',
        'date': '2026-02-01',
        'snippet': '...'
    },
    # ... 7 search results total
]
```

**Key findings:**
1. Citations appear in the chunk with `finish_reason='stop'`
2. This chunk **has choices** (not a usage-only chunk)
3. Both `citations` (array of URLs) and `search_results` (detailed objects) are present
4. They're attributes directly on the chunk object

## API Behavior Documentation

### Streaming Chunk Types

Perplexity streaming responses include two types of chunks:

1. **Content chunks** - Have `choices[0].delta.content` with text
2. **Finish chunk** - Has `choices[0].finish_reason='stop'` with citations

### Citation Format

```python
# Direct attributes on the chunk object
chunk.citations: list[str]  # Array of URL strings
chunk.search_results: list[dict]  # Array of detailed result objects

# search_results structure
{
    'title': str,        # Page title
    'url': str,          # Source URL
    'date': str,         # Publication date (YYYY-MM-DD)
    'last_updated': str, # Last update date
    'snippet': str,      # Text excerpt
    'source': 'web'      # Source type
}
```

## The Fix

Updated `perplexity_provider.py` to extract citations from the finish chunk:

```python
# Check finish reason for edge cases
if chunk.choices[0].finish_reason:
    finish_reason = chunk.choices[0].finish_reason

    # Extract citations/search_results from finish chunk
    if metadata is not None:
        citations = self._extract_citations(chunk)
        if citations:
            metadata["citations"] = citations
            self._mark_search_executed(metadata, "citations")
        search_results = self._extract_search_results(chunk)
        if search_results:
            metadata["search_results"] = search_results
            self._mark_search_executed(metadata, "search_results")
```

### Changes Made

**File:** `src/polychat/ai/perplexity_provider.py`

**Location:** Lines ~254-265 (in the `send_message` streaming loop)

**What changed:**
- Added citation extraction when `finish_reason` is present
- Now checks both:
  1. Chunks without choices (usage-only chunks) - for backward compatibility
  2. Chunks with `finish_reason` (finish chunks) - **where citations actually are**

## Supporting Evidence

### Official and Community Sources

1. **LiteLLM Issue #13777** - ["Perplexity doesn't return citations when streaming=True"](https://github.com/BerriAI/litellm/issues/13777)
   - Confirms: "Citations are still available in each chunk when streaming responses"
   - Access via: `first_chunk.citations` directly from chunk objects

2. **LiteLLM Issue #5535** - ["Perplexity model w/ stream=true and return_citations=true doesn't work"](https://github.com/BerriAI/litellm/issues/5535)
   - Shows raw API response with citations as a field within streaming chunks
   - Resolved via PR #5567 which added proper citation handling
   - Citations appear alongside standard fields: `id`, `model`, `usage`, `choices`

3. **Perplexity Streaming Documentation** - [docs.perplexity.ai/guides/streaming-responses](https://docs.perplexity.ai/guides/streaming-responses)
   - References `citations` and `search_results` fields in API responses
   - Notes: "To ensure all links are valid, use the links returned in the citations or search_results fields"

4. **LiteLLM Provider Docs** - [docs.litellm.ai/docs/providers/perplexity](https://docs.litellm.ai/docs/providers/perplexity)
   - Documents streaming with citations support
   - Notes historical issues with citation extraction

### Known Issues Across Ecosystem

Multiple projects have encountered this same issue:
- **gptel** (Emacs client) - [Issue #299](https://github.com/karthink/gptel/issues/299)
- **LibreChat** - [Discussion #4692](https://github.com/danny-avila/LibreChat/discussions/4692)
- **OpenAI Agents** - [Issue #1346](https://github.com/openai/openai-agents-python/issues/1346)

This confirms it's a common misunderstanding about Perplexity's streaming API structure.

## Implementation Details

### Extraction Methods

The provider uses two extraction methods:

```python
@classmethod
def _extract_citations(cls, payload: object) -> list[dict]:
    """Extract citations with best available title information.

    Prefers search_results (includes titles) over legacy citations field.
    Returns normalized format: [{"url": str, "title": str}, ...]
    """
    # 1. Try search_results first (has titles)
    search_results = cls._extract_search_results(payload)
    if search_results:
        return [{"url": r.get("url"), "title": r.get("title")}
                for r in search_results if r.get("url")]

    # 2. Fallback to citations array (URLs only)
    citations = getattr(payload, "citations", None) or []
    return [{"url": c, "title": None} for c in citations if c]

@staticmethod
def _extract_search_results(payload: object) -> list[dict]:
    """Extract search_results into normalized citation-like records.

    Returns: [{"url": str, "title": str, "date": str}, ...]
    """
    results = getattr(payload, "search_results", None) or []
    normalized = []
    for item in results:
        url = item.get("url") if isinstance(item, dict) else getattr(item, "url", None)
        title = item.get("title") if isinstance(item, dict) else getattr(item, "title", None)
        date = item.get("date") if isinstance(item, dict) else getattr(item, "date", None)
        if url:
            normalized.append({"url": url, "title": title, "date": date})
    return normalized
```

### Why Two Fields?

Perplexity provides both:
- **`citations`**: Simple array of URL strings (legacy format)
- **`search_results`**: Rich objects with title, snippet, date, etc.

We prefer `search_results` because it includes titles, which provide better context in the "Sources:" display.

## Testing

### Manual Test

```bash
poetry run pc -p ~/profile.json
/perp
what's the weather in tokyo today?
```

**Expected result:**
- Response text with `[1]`, `[2]` markers
- "Sources:" section at the end with clickable links
- Each source shows title and URL

### Debug Test

To verify citations are being extracted:

```python
# In repl.py, after streaming completes:
print(f"Citations: {metadata.get('citations')}")
print(f"Search results: {metadata.get('search_results')}")
```

Should show populated arrays, not `None`.

## Native Search Behavior

Perplexity's "sonar" models always search by default (hence "native_search_model" in logs). The `/search` mode flag doesn't control whether Perplexity searches - it always does. Instead:

- `/search on` - Makes best effort to enable search for other providers
- `/search off` - Doesn't prevent Perplexity from searching
- **Citations always displayed/logged** regardless of `/search` setting

This is documented in the main README.md under the principle: "Citations and thoughts should always be displayed and logged when present in responses."

## Related Files

- `src/polychat/ai/perplexity_provider.py` - Main provider implementation
- `src/polychat/streaming.py` - `display_citations()` function
- `src/polychat/repl.py` - Citation enrichment and display logic
- `src/polychat/chat.py` - `add_assistant_message()` with citations parameter
- `README.md` - User-facing documentation

## Future Considerations

### API Changes

Perplexity's API structure may evolve:
- Citation format could change
- New fields might be added
- `search_results` structure might expand

### Monitoring

Watch for:
- Changes in chunk structure
- New citation-related fields
- Updates to Perplexity's official documentation

### Similar Issues

Other providers may have similar quirks:
- Claude: Citations in specific content blocks
- Gemini: Search results in grounding metadata
- Grok: Citations in x/web search results

Each provider's citation extraction should be tested independently.

## References

### Official Documentation
- [Perplexity API Docs](https://docs.perplexity.ai/)
- [Perplexity Streaming Guide](https://docs.perplexity.ai/guides/streaming-responses)
- [Perplexity API Platform](https://www.perplexity.ai/api-platform)

### Community Issues
- [LiteLLM #13777 - Citations when streaming](https://github.com/BerriAI/litellm/issues/13777)
- [LiteLLM #5535 - stream=true and return_citations](https://github.com/BerriAI/litellm/issues/5535)
- [LiteLLM #5313 - return_citations while streaming](https://github.com/BerriAI/litellm/issues/5313)
- [gptel #299 - Perplexity citations](https://github.com/karthink/gptel/issues/299)

### Related
- [LiteLLM Perplexity Provider](https://docs.litellm.ai/docs/providers/perplexity)
- [OpenWebUI Perplexity Function](https://openwebui.com/f/yazon/perplexity_sonar_api_with_citations)

---

**Last Updated:** February 10, 2026
**Tested With:** Perplexity API (sonar model)
**OpenAI SDK Version:** 1.x
**Status:** Working as expected
