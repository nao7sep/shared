# Poly-Chat Provider Search Capability Check (2026-02-09)

Date checked: February 9, 2026

## Providers in polychat (7)

From `apps/polychat/src/polychat/models.py`:

- openai
- claude (Anthropic)
- gemini
- grok (xAI)
- perplexity
- mistral
- deepseek

## Package usage in polychat

- OpenAI provider uses Responses API (`openai` SDK):
  - `apps/polychat/src/polychat/ai/openai_provider.py`
- Gemini provider uses Google SDK:
  - `apps/polychat/src/polychat/ai/gemini_provider.py`
- Claude provider uses Anthropic SDK:
  - `apps/polychat/src/polychat/ai/claude_provider.py`
- Other 4 providers use OpenAI-compatible `openai` SDK:
  - `apps/polychat/src/polychat/ai/grok_provider.py`
  - `apps/polychat/src/polychat/ai/perplexity_provider.py`
  - `apps/polychat/src/polychat/ai/mistral_provider.py`
  - `apps/polychat/src/polychat/ai/deepseek_provider.py`

## Official search support (latest docs)

- OpenAI: Yes (official web search tool)
- Anthropic (Claude): Yes (official web search tool)
- Gemini (Google): Yes (grounding with Google Search)
- xAI (Grok): Yes (Live Search)
- Perplexity: Yes (Search API)
- Mistral: Yes (built-in web search tools)
- DeepSeek: No clear first-party official web-search API feature in current public API docs

## Sources

- OpenAI web search: https://developers.openai.com/api/docs/guides/tools-web-search
- Anthropic web search: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
- Gemini Google Search grounding: https://ai.google.dev/gemini-api/docs/google-search
- xAI Live Search: https://docs.x.ai/docs/guides/live-search
- Perplexity Search API: https://docs.perplexity.ai/docs/search/quickstart
- Mistral web search tool: https://docs.mistral.ai/agents/tools/built-in/websearch
- DeepSeek API docs index: https://api-docs.deepseek.com/
