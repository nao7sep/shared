# AI Provider Search Features Comparison (2026)

> **Last Updated:** February 10, 2026
> **Research conducted using Claude Sonnet 4.5**

This document provides a comprehensive overview of search capabilities across all 7 AI providers supported in PolyChat.

---

## Table of Contents

1. [Overview](#overview)
2. [Providers with Search Support](#providers-with-search-support)
3. [Providers without Search Support](#providers-without-search-support)
4. [Implementation Details](#implementation-details)
5. [Pricing Comparison](#pricing-comparison)
6. [References](#references)

---

## Overview

**PolyChat's 7 AI Providers:**

1. **OpenAI** - Uses OpenAI Responses API
2. **Gemini (Google)** - Uses Google's own `genai` package
3. **Anthropic (Claude)** - Uses Anthropic's own package
4. **Perplexity** - Uses OpenAI package (OpenAI-compatible API)
5. **DeepSeek** - Uses OpenAI package (OpenAI-compatible API)
6. **Mistral** - Uses OpenAI package (OpenAI-compatible API)
7. **Grok (xAI)** - Uses OpenAI package (OpenAI-compatible API)

**Search Support Summary:** 6 out of 7 providers officially support search features as of February 2026.

---

## Providers with Search Support

### 1. Perplexity ⭐ (Native Search Specialist)

**Status:** Native search provider - purpose-built for search

**Features:**
- Dedicated Search API with Sonar models specifically designed for search
- Built-in citations feature (implemented in `perplexity_provider.py` line 249)
- Official SDKs for Python and TypeScript/JavaScript
- Search SDK with one-click installation for Cursor, VS Code, and Claude Desktop
- MCP Server support

**Pricing:**
- Search API: **$5 per 1,000 requests**
- Sonar models: **$1 per million tokens** (input/output)

**API Parameters:**
- `max_tokens` - Control maximum tokens extracted per page
- `last_updated_filter` - Filter results by content update date

**Use Cases:**
- News aggregators
- Research tools
- Personalized assistants requiring real-time information

**Documentation:**
- [Perplexity Search API](https://www.perplexity.ai/hub/blog/introducing-the-perplexity-search-api)
- [Sonar Pro API](https://www.perplexity.ai/hub/blog/introducing-the-sonar-pro-api)
- [API Platform](https://www.perplexity.ai/api-platform)

---

### 2. Gemini (Google) ⭐

**Status:** Officially supported via Grounding with Google Search

**Features:**
- Grounding with Google Search connects Gemini to real-time web content
- Provides accurate answers with verifiable source citations
- Grounding with Google Maps also available
- Can enable both Google Search and Google Maps in the same request

**Pricing:**
- **Gemini 3:** Billed per search query (multiple queries in one call = multiple billable uses)
- **Gemini 2.5 and older:** Billed per prompt
- Billing started: January 5, 2026

**Supported Models:**
- Gemini 3 (current generation)
- Gemini 2.5 (previous generation)

**Context Window:**
- Supports grounding across full context window

**Documentation:**
- [Grounding with Google Search (Gemini API)](https://ai.google.dev/gemini-api/docs/google-search)
- [Grounding with Google Search (Vertex AI)](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-search)
- [Firebase AI Logic Grounding](https://firebase.google.com/docs/ai-logic/grounding-google-search)
- [Gemini API Announcement](https://developers.googleblog.com/en/gemini-api-and-ai-studio-now-offer-grounding-with-google-search/)

---

### 3. OpenAI ⭐

**Status:** Search-enhanced models launched October 2026

**Features:**
- Specialized search-enhanced models with embedded web search functionality
- Agentic search with reasoning models - model actively manages search process
- Performs web searches as part of chain of thought
- Analyzes results and decides whether to continue searching
- Delivers cited answers with real-time information

**Available Models:**
- `gpt-5-search-api` (latest)
- `gpt-5-search-api-2026-10-14` (dated variant)
- `gpt-4o-search-preview`
- `gpt-4o-mini-search-preview`

**Limitations:**
- Not supported in: `gpt-5` with minimal reasoning, `gpt-4.1-nano`
- Context window limited to 128,000 tokens (even with `gpt-4.1` and `gpt-4.1-mini`)

**Use Cases:**
- News aggregators
- Research tools
- Personalized assistants
- Applications requiring live data

**Documentation:**
- [Web Search Guide](https://platform.openai.com/docs/guides/tools-web-search)
- [GPT-4o Search Preview Model](https://platform.openai.com/docs/models/gpt-4o-search-preview)
- [API Platform](https://openai.com/api/)

---

### 4. Anthropic (Claude) ⭐

**Status:** Web search API officially launched for latest models

**Features:**
- Web search tool available via API
- Web fetch tool for analyzing specific webpage URLs
- Claude uses reasoning to determine when web search would help
- Provides real-time information with citations
- Particularly valuable for accessing current API documentation and technical articles

**Pricing:**
- **$10 per 1,000 searches** plus standard token costs

**Supported Models:**
- Claude 3.7 Sonnet
- Claude 3.5 Sonnet (upgraded)
- Claude 3.5 Haiku

**Use Cases:**
- Up-to-date AI applications
- Claude Code with access to current documentation
- Technical research with version-specific API references
- Troubleshooting obscure errors
- Working with new or rapidly evolving frameworks

**Documentation:**
- [Introducing web search on the Anthropic API](https://claude.com/blog/web-search-api)
- [Web search with Claude on Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude/web-search)

---

### 5. Mistral ⭐

**Status:** Web search available via Agents API

**Features:**
- Web search offered as a connector in Agents API
- Combines Mistral models with up-to-date information
- Access to web search, reputable news, and other sources
- Premium News Access with integrated news provider verification
- Part of comprehensive Agents API (also includes code execution, image generation, RAG)

**Pricing:**
- Web Search Connector: **$30 per 1,000 calls**
- Premium News Access: **$50 per 1,000 calls**

**Performance (SimpleQA Benchmark):**
- Mistral Large with web search: **75%** (vs 23% without)
- Mistral Medium with web search: **82.32%** (vs 22.08% without)

**Features:**
- Browse the web for information
- Access recent information beyond training data cutoff
- Access specific websites
- Retrieve from verified news providers

**Documentation:**
- [Mistral Agents API](https://mistral.ai/news/agents-api)
- [Websearch Documentation](https://docs.mistral.ai/agents/tools/built-in/websearch)
- [Mistral AI Models](https://mistral.ai/models)

---

### 6. Grok (xAI) ⭐

**Status:** Dual search capabilities (Web Search + X Search)

**Features:**
- **Web Search:** Real-time web search and page browsing
- **X Search:** Keyword search, semantic search, user search, and thread fetch on X (Twitter)
- Agentic search capabilities - iteratively calls search tools
- `grok-4-1-fast` specifically trained for agentic search
- Model automatically determines which tool to use (or both)
- Collections API for retrieval across finance, legal, and coding domains

**Search Tools:**
- `web_search` - Search and browse web pages
- `x_search` - Search X platform (formerly Twitter)
- Can use both simultaneously for comprehensive search

**Agentic Search:**
- Iteratively calls search tools
- Analyzes responses and makes follow-up queries
- Navigates web pages and X posts seamlessly
- Uncovers difficult-to-find information and insights

**Important Note:**
- Live Search API deprecated on January 12, 2026
- Switch to Tools function calling method

**Documentation:**
- [Web Search Guide](https://docs.x.ai/docs/guides/tools/search-tools)
- [Search Tools Overview](https://docs.x.ai/docs/guides/live-search)
- [Tools Overview](https://docs.x.ai/docs/guides/tools/overview)
- [xAI API](https://x.ai/api)
- [Grok Collections API](https://x.ai/news/grok-collections-api)

---

## Providers without Search Support

### 7. DeepSeek ❌

**Status:** No official search API (as of February 2026)

**Current Situation:**
- DeepSeek does NOT currently offer built-in search functionality
- API uses OpenAI-compatible format but without search features
- Can connect to external search via third-party tools (e.g., SerpAPI)

**Future Plans (Announced):**
- Planning multimodal AI search engine processing text, images, and audio
- Will accept screenshots, voice recordings, and photos as direct inputs
- Developing persistent AI agents for autonomous task execution
- Example use case: Agent monitors prices, compares options, executes purchases

**Planned Launch Options:**
1. Standalone app competing with Google
2. API for third-party applications
3. Embedded within DeepSeek's existing chat interface

**Strategic Approach:**
- API strategy could enable thousands of applications to integrate DeepSeek search
- Bypasses battle for Android/iOS home screens
- Users may not consciously choose it but get it through integrated apps

**Current API:**
- OpenAI-compatible API format
- Can modify configuration to use OpenAI SDK
- No built-in search capabilities yet

**Workaround:**
- [Connect DeepSeek API with real-time data](https://serpapi.com/blog/connect-deepseek-api-with-the-internet-google-search-and-more/)

**Documentation:**
- [DeepSeek API Docs](https://api-docs.deepseek.com/)
- [Multimodal AI Search Announcement](https://winbuzzer.com/2026/01/29/deepseek-targets-google-multimodal-ai-search-xcxwbn/)
- [DeepSeek Official Site](https://www.deepseek.com/en/)

---

## Implementation Details

### PolyChat Provider Architecture

**Providers using their own SDKs:**
1. OpenAI - Uses OpenAI Responses API (`AsyncOpenAI` with `responses.create`)
2. Gemini - Uses Google's `genai` package (`genai.Client`)
3. Anthropic - Uses Anthropic SDK (`AsyncAnthropic`)

**Providers using OpenAI SDK (OpenAI-compatible):**
4. Perplexity - `AsyncOpenAI` with `base_url="https://api.perplexity.ai"`
5. DeepSeek - `AsyncOpenAI` with `base_url="https://api.deepseek.com"`
6. Mistral - `AsyncOpenAI` with `base_url="https://api.mistral.ai/v1"`
7. Grok - `AsyncOpenAI` with `base_url="https://api.x.ai/v1"`

### Code References

**Provider implementations:**
- `/apps/polychat/src/polychat/ai/openai_provider.py` - OpenAI Responses API
- `/apps/polychat/src/polychat/ai/gemini_provider.py` - Google genai SDK
- `/apps/polychat/src/polychat/ai/claude_provider.py` - Anthropic SDK
- `/apps/polychat/src/polychat/ai/perplexity_provider.py` - OpenAI-compatible (line 249: citations)
- `/apps/polychat/src/polychat/ai/deepseek_provider.py` - OpenAI-compatible
- `/apps/polychat/src/polychat/ai/mistral_provider.py` - OpenAI-compatible
- `/apps/polychat/src/polychat/ai/grok_provider.py` - OpenAI-compatible

---

## Pricing Comparison

| Provider | Search Pricing | Notes |
|----------|---------------|-------|
| **Perplexity** | $5 / 1K requests | Dedicated search API; Sonar models $1/M tokens |
| **Gemini** | Per query (Gemini 3) or per prompt (older) | Billing started Jan 5, 2026 |
| **OpenAI** | Included in model pricing | Search-enhanced models; context limited to 128K |
| **Anthropic** | $10 / 1K searches + tokens | Claude 3.7 Sonnet, 3.5 Sonnet, 3.5 Haiku |
| **Mistral** | $30 / 1K calls | Premium News: $50 / 1K calls |
| **Grok** | Unknown | Pricing not publicly disclosed yet |
| **DeepSeek** | N/A | No search feature available |

---

## References

### Official Documentation Links

**Perplexity:**
- [Perplexity Search API](https://www.perplexity.ai/hub/blog/introducing-the-perplexity-search-api)
- [Sonar Pro API](https://www.perplexity.ai/hub/blog/introducing-the-sonar-pro-api)
- [API Platform](https://www.perplexity.ai/api-platform)
- [Changelog](https://docs.perplexity.ai/changelog/changelog)

**Gemini:**
- [Grounding with Google Search (Gemini API)](https://ai.google.dev/gemini-api/docs/google-search)
- [Grounding with Google Search (Vertex AI)](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-search)
- [Firebase AI Logic Grounding](https://firebase.google.com/docs/ai-logic/grounding-google-search)
- [Official Blog Announcement](https://developers.googleblog.com/en/gemini-api-and-ai-studio-now-offer-grounding-with-google-search/)

**OpenAI:**
- [Web Search Guide](https://platform.openai.com/docs/guides/tools-web-search)
- [GPT-4o Search Preview Model](https://platform.openai.com/docs/models/gpt-4o-search-preview)
- [ChatGPT Search Announcement](https://openai.com/index/introducing-chatgpt-search/)
- [API Platform](https://platform.openai.com/docs/models)

**Anthropic:**
- [Web Search API Announcement](https://claude.com/blog/web-search-api)
- [Web search with Claude on Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude/web-search)

**Mistral:**
- [Agents API Announcement](https://mistral.ai/news/agents-api)
- [Websearch Documentation](https://docs.mistral.ai/agents/tools/built-in/websearch)
- [Mistral AI Models](https://mistral.ai/models)

**Grok (xAI):**
- [Web Search Guide](https://docs.x.ai/docs/guides/tools/search-tools)
- [Search Tools Overview](https://docs.x.ai/docs/guides/live-search)
- [Tools Overview](https://docs.x.ai/docs/guides/tools/overview)
- [xAI API](https://x.ai/api)

**DeepSeek:**
- [DeepSeek API Docs](https://api-docs.deepseek.com/)
- [Multimodal Search Plans](https://winbuzzer.com/2026/01/29/deepseek-targets-google-multimodal-ai-search-xcxwbn/)
- [DeepSeek Official Site](https://www.deepseek.com/en/)
- [SerpAPI Integration Guide](https://serpapi.com/blog/connect-deepseek-api-with-the-internet-google-search-and-more/)

---

## Conclusion

As of February 2026, **6 out of 7** AI providers in PolyChat officially support search features:

✅ **Perplexity** (native search specialist)
✅ **Gemini** (Google Search grounding)
✅ **OpenAI** (search-enhanced models)
✅ **Anthropic** (web search + web fetch tools)
✅ **Mistral** (Agents API with search connector)
✅ **Grok** (dual web + X platform search)

❌ **DeepSeek** (planned but not yet available)

**Recommendation for PolyChat users:**
- For search-intensive tasks, use **Perplexity** (purpose-built for search)
- For Google-powered search, use **Gemini**
- For reasoning + search, use **OpenAI** search-enhanced models or **Grok** agentic search
- For verified news access, use **Mistral** with Premium News Access
- For current documentation while coding, use **Claude** with web search enabled

---

*This research was conducted by Claude Sonnet 4.5 on February 10, 2026, using web search to gather the latest information about AI provider search capabilities.*
