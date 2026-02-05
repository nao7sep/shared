# Internal Documentation Index

This directory contains reference documentation for integrating various AI providers into poly-chat. These documents serve as guides for understanding chat API usage, timeout/retry support, error handling, and provider-specific edge cases.

## Document Overview

### Origins and Context

The [provider-guide.md](provider-guide.md) was created as a quick-start reference during the initial implementation of poly-chat's multi-provider architecture. It covers all providers in a single document but may lack depth in certain areas.

The remaining documents were generated using Gemini's Deep Research feature to provide more comprehensive coverage of each provider's chat API specifics—including timeout configuration, retry strategies, error handling patterns, and edge cases.

**Notes on specific documents:**
- Two OpenAI guides exist because the first research accidentally included the newer Responses API; the second focuses exclusively on the legacy Chat Completions API (which is poly-chat's current scope)
- Two Anthropic guides exist: the Japanese version was generated when the research was conducted from a Japan-based IP (resulting in Japanese sources being heavily referenced), while the English version was created subsequently; the Japanese document references more source material and may contain additional value

---

## Document Catalog

### 1. [provider-guide.md](provider-guide.md)
**AI Provider Implementation Guide**

A consolidated reference covering all supported AI providers. Created during poly-chat's provider implementation phase as a single-shot overview.

**Contents:**
- Critical vs. optional implementation requirements
- Error handling patterns with SDK-specific error classes (OpenAI, Anthropic, Google, etc.)
- Timeout management strategies across providers
- Metadata extraction templates for each provider (token usage, finish reasons, etc.)
- Provider-specific features (reasoning content for DeepSeek, citations for Perplexity)

**Best for:** Quick lookup of implementation patterns across multiple providers

---

### 2. [openai-integration-patterns-2026.md](openai-integration-patterns-2026.md)
**Architectural Patterns for Production-Grade OpenAI Integration (2026)**

Comprehensive technical report covering both the legacy Chat Completions API and the newer Responses API.

**Contents:**
- Client architecture and network configuration (httpx, connection pooling)
- Granular timeout configuration (connect, read, write, pool)
- The Responses API: stateful context management, agentic loops, `store=true` pattern
- Retry mathematics with exponential backoff and jitter
- Structured Outputs with Pydantic integration

**Note:** This document includes coverage of the Responses API, which is outside poly-chat's current scope. See the next document for Chat Completions-focused guidance.

**Best for:** Understanding advanced OpenAI patterns, including the Responses API

---

### 3. [openai-integration-guide.md](openai-integration-guide.md)
**The Definitive Guide to Robust Integration with the OpenAI Python SDK (Legacy Chat Completions)**

Focused exclusively on the Chat Completions API (`client.chat.completions.create`), which is poly-chat's primary integration target.

**Contents:**
- SDK v1.0+ architecture shift (instance-based clients, httpx transport)
- Timeout management strategies with `httpx.Timeout`
- Message payload structure (system/user/assistant roles, context window management)
- Critical control parameters (`temperature`, `top_p`, `max_tokens`, `seed`, penalties)
- Response object structure and `finish_reason` handling
- Streaming implementation with Server-Sent Events (SSE)
- Delta vs. Message structure in streaming responses

**Best for:** Implementing OpenAI Chat Completions in poly-chat

---

### 4. [google-genai-reference.md](google-genai-reference.md)
**Engineering Production-Grade Applications with the google-genai Python SDK**

Technical reference for the new unified `google-genai` SDK (v1.0+), which replaces the legacy `google-generativeai` package.

**Contents:**
- Ecosystem unification (Gemini Developer API and Vertex AI via single client)
- Client initialization and dual-mode authentication (API key vs. ADC)
- **Critical timeout nuance: units are in milliseconds, not seconds**
- `types.HttpOptions` and `types.HttpRetryOptions` configuration
- Retriable vs. non-retriable error codes
- Production retry policy implementation

**Best for:** Implementing Gemini integration with proper timeout configuration

---

### 5. [anthropic-python-sdk-guide.md](anthropic-python-sdk-guide.md)
**Anthropic Python SDK エンジニアリング包括的ガイド** *(Japanese)*

Comprehensive guide for the Anthropic Python SDK (v0.77.0+), written in Japanese.

**Contents:**
- SDK architecture overview (httpx-based, Pydantic validation)
- Messages API with polymorphic content blocks (text, image, document)
- Async processing with `AsyncAnthropic` and `asyncio.gather`
- Streaming with Extended Thinking (`thinking_delta` events)
- Timeout configuration with `httpx.Timeout` (default: 10 minutes)
- Retry logic and exception hierarchy (`OverloadedError` 529 handling)
- Prompt Caching implementation with `cache_control`
- Structured Outputs with Pydantic (`output_config` migration)
- MCP integration and Computer Use (Beta)

**Note:** This Japanese version was generated when the research referenced predominantly Japanese sources. It includes more extensive source material than the English version and may contain additional insights.

**Best for:** Detailed Anthropic implementation reference (Japanese readers, or for cross-referencing)

---

### 6. [anthropic-sdk-reference.md](anthropic-sdk-reference.md)
**The Architect's Guide to the Anthropic Python SDK (2026 Edition)** *(English)*

English-language guide for the Anthropic Python SDK, covering the same SDK but from English source material.

**Contents:**
- Package design and dependency management (`anthropic[vertex]`, `anthropic[bedrock]`)
- Versioning strategy and breaking changes (v0.77.0 `output_config` migration)
- Environment configuration and proxy setup
- Messages API anatomy (role constraints, system prompt separation)
- Multimodal inputs and base64 image handling
- Context window management with `count_tokens()`
- Timeout configuration and latency-throughput tradeoffs
- Retry strategies and idempotency

**Note:** The filename was adjusted to avoid collision with the Japanese version.

**Best for:** Anthropic implementation reference (English readers)

---

### 7. [xai-grok-openai-integration.md](xai-grok-openai-integration.md)
**Comprehensive Integration Analysis: xAI Grok API via OpenAI SDK**

Technical reference for integrating xAI's Grok models using the OpenAI Python SDK.

**Contents:**
- Protocol compatibility with OpenAI API specification
- Client configuration with `base_url="https://api.x.ai/v1"`
- Grok model family (Grok-4, Grok-4-1-fast-reasoning, Grok-4-1-fast-non-reasoning)
- Reasoning tokens and economic implications
- Parameter nuances (`temperature`, `max_tokens` behavior with reasoning models)
- Multi-turn conversation state management
- Advanced transport configuration (proxy, connection pooling)

**Best for:** Implementing Grok integration via OpenAI SDK

---

### 8. [mistral-openai-integration.md](mistral-openai-integration.md)
**Comprehensive Technical Analysis: Mistral AI via OpenAI Python SDK**

Technical reference for integrating Mistral AI using the OpenAI Python SDK.

**Contents:**
- API compatibility layer (syntactic vs. semantic compatibility)
- Client instantiation with `base_url="https://api.mistral.ai/v1"`
- Supported parameter matrix (which OpenAI params work with Mistral)
- `extra_body` pattern for Mistral-specific parameters (`safe_prompt`)
- **Critical: `stream_options` incompatibility causing 422 errors**
- Granular timeout configuration with `httpx.Timeout`
- Tokenization differences (`mistral-common` vs. `tiktoken`)

**Best for:** Implementing Mistral integration with awareness of compatibility pitfalls

---

### 9. [perplexity-api-guide.md](perplexity-api-guide.md)
**Perplexity API Integration Guide: OpenAI Python SDK Implementation**

Technical reference for integrating Perplexity's search-enabled AI using the OpenAI Python SDK.

**Contents:**
- Model landscape: Sonar family (`sonar`, `sonar-pro`, `sonar-reasoning-pro`, `sonar-deep-research`)
- Client configuration with extended read timeouts (critical for search latency)
- Synchronous chat implementation
- Deep Research architecture (asynchronous job submission and polling)
- Metadata extraction including citations
- Error handling for search-dependent operations

**Best for:** Implementing Perplexity integration with proper latency handling

---

### 10. [deepseek-api-integration.md](deepseek-api-integration.md)
**DeepSeek API Integration Strategy: Resilience, Reasoning, and Architecture (2026)**

Technical reference for integrating DeepSeek models (V3.2 and R1 reasoner) via the OpenAI Python SDK.

**Contents:**
- Client configuration with extended timeouts (5-minute read timeout recommended)
- Model architecture: `deepseek-chat` vs. `deepseek-reasoner`
- **Critical: `reasoning_content` field handling in R1 models**
- Parameter constraints in reasoning mode (temperature/top_p ignored, logprobs forbidden)
- Streaming with usage statistics in final chunk
- "Server Busy" (503) resilience patterns
- Disk-based context caching economics

**Best for:** Implementing DeepSeek integration with proper reasoning model support

---

## Quick Reference

| Provider | Document | Key Concerns |
|----------|----------|--------------|
| All | [provider-guide.md](provider-guide.md) | Overview, basic patterns |
| OpenAI | [openai-integration-guide.md](openai-integration-guide.md) | Chat Completions focus |
| OpenAI | [openai-integration-patterns-2026.md](openai-integration-patterns-2026.md) | Includes Responses API |
| Google | [google-genai-reference.md](google-genai-reference.md) | **Timeout in milliseconds** |
| Anthropic | [anthropic-sdk-reference.md](anthropic-sdk-reference.md) | English version |
| Anthropic | [anthropic-python-sdk-guide.md](anthropic-python-sdk-guide.md) | Japanese, more sources |
| xAI Grok | [xai-grok-openai-integration.md](xai-grok-openai-integration.md) | Reasoning tokens |
| Mistral | [mistral-openai-integration.md](mistral-openai-integration.md) | `stream_options` 422 error |
| Perplexity | [perplexity-api-guide.md](perplexity-api-guide.md) | Search latency handling |
| DeepSeek | [deepseek-api-integration.md](deepseek-api-integration.md) | `reasoning_content` field |
