# PolyChat AI Providers Analysis - Copilot Research

**Analysis Date:** February 9, 2026

## The 7 AI Providers in PolyChat

### 1. OpenAI Provider
- **Location:** `apps/poly-chat/src/poly_chat/ai/openai_provider.py`
- **Implementation:** Uses OpenAI Responses API (recommended for all new projects)
- **Package:** `openai` (AsyncOpenAI)
- **Notes:** Uses the official OpenAI SDK with Responses API

### 2. Claude (Anthropic) Provider
- **Location:** `apps/poly-chat/src/poly_chat/ai/claude_provider.py`
- **Implementation:** Uses Anthropic's own SDK
- **Package:** `anthropic` (AsyncAnthropic)
- **Notes:** Uses the official Anthropic SDK

### 3. Gemini (Google) Provider
- **Location:** `apps/poly-chat/src/poly_chat/ai/gemini_provider.py`
- **Implementation:** Uses Google's own genai SDK
- **Package:** `google.genai`
- **Notes:** Uses the official Google Generative AI SDK

### 4. Perplexity Provider
- **Location:** `apps/poly-chat/src/poly_chat/ai/perplexity_provider.py`
- **Implementation:** Uses OpenAI-compatible API
- **Package:** `openai` (AsyncOpenAI)
- **Notes:** Uses OpenAI package to reduce complexity

### 5. Mistral Provider
- **Location:** `apps/poly-chat/src/poly_chat/ai/mistral_provider.py`
- **Implementation:** Uses OpenAI-compatible API
- **Package:** `openai` (AsyncOpenAI)
- **Notes:** Uses OpenAI package to reduce complexity

### 6. Grok (xAI) Provider
- **Location:** `apps/poly-chat/src/poly_chat/ai/grok_provider.py`
- **Implementation:** Uses OpenAI-compatible API
- **Package:** `openai` (AsyncOpenAI)
- **Notes:** Uses OpenAI package to reduce complexity

### 7. DeepSeek Provider
- **Location:** `apps/poly-chat/src/poly_chat/ai/deepseek_provider.py`
- **Implementation:** Uses OpenAI-compatible API
- **Package:** `openai` (AsyncOpenAI)
- **Notes:** Uses OpenAI package to reduce complexity

## Official Search Feature Support (2026)

### ✅ Providers WITH Official Search Features

#### 1. Google Gemini - **FULL SUPPORT**
- **Status:** Fully supports official search grounding using Google Search
- **Features:**
  - Native Google Search grounding with inline citations
  - Available in Gemini API and Google AI Studio
  - Full audit trail for citations
  - Emphasized as a differentiator for freshness and factuality
- **Best For:** Real-time factual information with Google Search integration

#### 2. Perplexity - **CORE FEATURE**
- **Status:** Built around real-time search grounding with citations
- **Features:**
  - Search grounding as default functionality
  - Pulls from variety of web and trusted sources
  - Citations included in responses
  - Focused on live retrieval and research-backed answers
- **Best For:** Research-oriented queries requiring multiple source citations

#### 3. OpenAI - **SUPPORTED**
- **Status:** Official search grounding via plugins and API integrations
- **Features:**
  - Browsing and web retrieval modes available
  - ChatGPT supports web search with citations
  - API can integrate with search via plugins
  - OpenRouter enables ":online" models for real-time web augmentation
- **Best For:** General-purpose AI with search augmentation when needed

#### 4. xAI Grok - **SUPPORTED**
- **Status:** Has official search grounding for real-time information
- **Features:**
  - Real-time conversational responses with source citations
  - Search-powered insights built into recent versions (e.g., Grok 4.1)
  - Up-to-date information capabilities
- **Best For:** Real-time conversational queries with current events

### ❌ Providers WITHOUT Native Search Features

#### 5. Anthropic Claude - **LIMITED**
- **Status:** Citations for enterprise/document sources only, NOT general web search
- **Features:**
  - API provides "Citations" feature
  - Works with user-uploaded reference documents
  - Enterprise data grounding (e.g., Amazon Bedrock)
  - Focused on private, verifiable sources
- **Note:** Does NOT support general internet search grounding

#### 6. Mistral - **NO NATIVE SUPPORT**
- **Status:** No official first-party search grounding feature
- **Features:** None (may work with third-party integrations)
- **Note:** Can be used with platforms like OpenRouter for web search, but not native

#### 7. DeepSeek - **NO NATIVE SUPPORT**
- **Status:** No public native web search grounding/citation feature
- **Features:** None (may work with third-party integrations)
- **Note:** No substantial evidence of dedicated search capability as of 2026

## Summary Table

| Provider | Official Search? | Implementation | Package Used | Search Type |
|----------|-----------------|----------------|--------------|-------------|
| **OpenAI** | ✅ Yes | Responses API | openai | Plugins/Browsing |
| **Claude** | ⚠️ Limited | Anthropic SDK | anthropic | Enterprise docs only |
| **Gemini** | ✅ Yes | Google SDK | google.genai | Google Search native |
| **Perplexity** | ✅ Yes | OpenAI-compatible | openai | Core feature |
| **Mistral** | ❌ No | OpenAI-compatible | openai | None |
| **Grok** | ✅ Yes | OpenAI-compatible | openai | Real-time search |
| **DeepSeek** | ❌ No | OpenAI-compatible | openai | None |

## Implementation Notes

### Package Usage Strategy
- **Own SDKs (3):** OpenAI, Claude, Gemini - Use their official packages for best support
- **OpenAI-Compatible (4):** Perplexity, Mistral, Grok, DeepSeek - Use OpenAI package to reduce complexity and dependencies

### Search Feature Recommendations
For search-enhanced queries in PolyChat:
1. **Best Choice:** Gemini or Perplexity (native search grounding)
2. **Good Choice:** OpenAI or Grok (search via plugins/features)
3. **Not Recommended:** Mistral, DeepSeek (no native search)
4. **Special Case:** Claude (only for enterprise document grounding, not web search)

## Sources
- Verified via web search on February 9, 2026
- Official documentation from provider websites
- Third-party analysis and comparison reports
- OpenRouter integration documentation
