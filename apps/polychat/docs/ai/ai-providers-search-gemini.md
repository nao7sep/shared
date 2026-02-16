# AI Providers and Search Capabilities (PolyChat)

This document summarizes the 7 AI providers integrated into `polychat` and their official support for web search/grounding features as of February 2026.

## Provider Implementation Details

The following providers are implemented in `apps/polychat/src/polychat/ai/`:

| Provider | Implementation Path | SDK / Integration Method |
| :--- | :--- | :--- |
| **OpenAI** | `openai_provider.py` | Official `openai` package (Native) |
| **Gemini** | `gemini_provider.py` | Official `google-genai` SDK |
| **Anthropic** | `claude_provider.py` | Official `anthropic` SDK |
| **Mistral** | `mistral_provider.py` | `openai` package (API Compatible) |
| **Grok (xAI)** | `grok_provider.py` | `openai` package (API Compatible) |
| **Perplexity** | `perplexity_provider.py` | `openai` package (API Compatible) |
| **DeepSeek** | `deepseek_provider.py` | `openai` package (API Compatible) |

## Official Search/Grounding Feature Support

Based on the latest industry data for 2026, here is the status of official, built-in search features accessible via API:

| Provider | Search Feature Name | Official API Support | Details |
| :--- | :--- | :--- | :--- |
| **Perplexity** | Pro Search / Native | **Yes** | Core "answer engine" feature. Optimized for research. |
| **OpenAI** | Search Tool (SearchGPT) | **Yes** | Integrated into GPT-4o and O-series models. |
| **Gemini** | Google Search Grounding | **Yes** | Official grounding in Google Search via Vertex AI/AI Studio. |
| **Anthropic** | Official Web Search Tool | **Yes** | Added May 2025. Available for Claude 3.5/3.7/4.x. |
| **Grok (xAI)** | Real-time Search | **Yes** | Direct access to real-time X (Twitter) and web data. |
| **Mistral** | Web Search Tool | **Yes** | Available via Mistral Agents API and latest large models. |
| **DeepSeek** | N/A | **No** | Not natively in the standard API (requires custom RAG). |

---
*Last Updated: 2026-02-10*
