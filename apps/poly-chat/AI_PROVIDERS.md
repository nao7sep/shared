# AI Provider Implementation Guide

This document provides comprehensive guidance for implementing AI providers in multi-provider chat applications. It covers critical error handling, timeout management, metadata extraction, and provider-specific features based on the latest API specifications (2026).

## Table of Contents

1. [Critical Implementation Requirements](#critical-implementation-requirements)
2. [Error Handling](#error-handling)
3. [Timeout Management](#timeout-management)
4. [Metadata Extraction](#metadata-extraction)
5. [Provider-Specific Features](#provider-specific-features)
6. [Testing Checklist](#testing-checklist)

---

## Critical Implementation Requirements

### What's Critical vs Over-Engineering

**CRITICAL (Must Have):**
- ✅ Timeout configuration (prevents app hanging)
- ✅ Basic error handling (prevents crashes)
- ✅ Error logging (for debugging)
- ✅ Basic metadata extraction (model name, token usage)

**Nice-to-Have (Don't Over-Engineer):**
- ⚠️ Retry logic with exponential backoff (only if needed)
- ⚠️ Provider-specific features (citations, reasoning content)
- ⚠️ Detailed token breakdowns
- ⚠️ Safety ratings, grounding metadata

### Philosophy

> For users, **WHY** an error occurs is often not important.
>
> What matters:
> 1. App doesn't freeze or crash
> 2. User can continue (e.g., by deleting last message)
> 3. Errors are logged for debugging

---

## Error Handling

### Basic Error Handling Pattern

All providers should wrap API calls with try-except blocks. Keep it simple:

```python
from typing import AsyncIterator
import traceback

async def send_message(
    self,
    messages: list[dict],
    model: str,
    system_prompt: str | None = None,
    stream: bool = True,
) -> AsyncIterator[str]:
    """Send message with error handling."""
    try:
        # Format messages
        formatted_messages = self.format_messages(messages)

        if system_prompt:
            formatted_messages.insert(0, {"role": "system", "content": system_prompt})

        # Create streaming request
        response = await self.client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            stream=stream,
            timeout=self.timeout,  # Use configured timeout
        )

        # Yield chunks
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        # Log error with full traceback
        error_msg = f"Provider error: {type(e).__name__}: {str(e)}"
        print(f"\n[ERROR] {error_msg}")

        # Optional: Log full traceback for debugging
        # traceback.print_exc()

        # Re-raise to let caller handle
        raise
```

### Error Serialization in Python

Python errors can be easily serialized to plaintext:

```python
import traceback

try:
    # API call
    pass
except Exception as e:
    # Simple error message
    error_simple = str(e)  # "Rate limit exceeded"

    # Error type + message
    error_typed = f"{type(e).__name__}: {str(e)}"  # "RateLimitError: Rate limit exceeded"

    # Full traceback (for logging)
    error_full = traceback.format_exc()
    # """
    # Traceback (most recent call last):
    #   File "...", line X, in send_message
    #     ...
    # RateLimitError: Rate limit exceeded
    # """

    # Log to file
    with open("error.log", "a") as f:
        f.write(f"\n[{datetime.now()}] {error_full}\n")
```

### Common Error Categories

All providers should handle these error types (names vary by SDK):

1. **Authentication Errors (401, 403)**
   - Invalid API key
   - Insufficient permissions
   - **Action:** Don't retry, show error to user

2. **Rate Limit Errors (429)**
   - Too many requests
   - **Action:** Optional retry with backoff, or just show error

3. **Timeout Errors**
   - Request took too long
   - **Action:** Show timeout message to user

4. **Server Errors (500, 503)**
   - Provider service down
   - **Action:** Show error, let user retry manually

5. **Validation Errors (400, 422)**
   - Invalid request format
   - **Action:** Show error (likely a bug in our code)

### SDK-Specific Error Classes

Different SDKs use different error class names:

**OpenAI SDK:**
```python
from openai import APIError, APITimeoutError, RateLimitError, AuthenticationError

try:
    response = await self.client.chat.completions.create(...)
except AuthenticationError as e:
    # 401
    print(f"Authentication failed: {e}")
except RateLimitError as e:
    # 429
    print(f"Rate limit exceeded: {e}")
except APITimeoutError as e:
    # Timeout
    print(f"Request timed out: {e}")
except APIError as e:
    # Other API errors (4xx, 5xx)
    print(f"API error: {e}")
```

**Anthropic SDK:**
```python
from anthropic import APIError, APITimeoutError, RateLimitError, AuthenticationError

try:
    async with self.client.messages.stream(...) as response_stream:
        async for text in response_stream.text_stream:
            yield text
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
except APITimeoutError as e:
    print(f"Request timed out: {e}")
except APIError as e:
    print(f"API error: {e}")
```

**Google GenAI SDK:**
```python
try:
    response = await self.client.aio.models.generate_content_stream(...)
except Exception as e:
    # Google SDK doesn't have specific error classes yet
    # Check for status codes in error message or use generic handling
    print(f"Gemini error: {e}")
```

---

## Timeout Management

### Why Timeouts are Critical

Without timeouts, the app will **hang indefinitely** if:
- Network connection is lost
- Provider API is unresponsive
- Request is queued on provider side

### Implementation

**1. Add timeout parameter to provider initialization:**

```python
class OpenAIProvider:
    def __init__(self, api_key: str, timeout: float = 30.0):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            timeout: Request timeout in seconds (default: 30.0, 0 = no timeout)
        """
        from openai import AsyncOpenAI

        # Convert 0 to None (no timeout)
        timeout_value = timeout if timeout > 0 else None

        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout_value,
        )
        self.timeout = timeout
```

**2. Add timeout to profile configuration:**

```json
{
  "default_ai": "claude",
  "timeout": 30,
  "models": { ... },
  ...
}
```

**3. Add /timeout command to change it:**

```
/timeout 60    - Set timeout to 60 seconds
/timeout 0     - Wait forever (no timeout)
/timeout       - Show current timeout
```

### Recommended Timeout Values

- **Default: 30 seconds** - Good balance for most use cases
- **Long context: 60-120 seconds** - For very long prompts
- **Streaming: 60 seconds** - First chunk should arrive within this time
- **No timeout (0): Use with caution** - Only for debugging or long-running tasks

### Provider-Specific Notes

- **OpenAI/Mistral/Grok/DeepSeek/Perplexity:** Use SDK's `timeout` parameter
- **Anthropic:** Use SDK's `timeout` parameter
- **Gemini:** Use `asyncio.timeout()` wrapper if SDK doesn't support timeout

```python
import asyncio

async def send_message_with_timeout(self, ...):
    if self.timeout > 0:
        async with asyncio.timeout(self.timeout):
            # API call here
            pass
    else:
        # No timeout
        # API call here
        pass
```

---

## Metadata Extraction

### Essential Metadata (All Providers)

Extract these fields in `get_full_response()`:

```python
metadata = {
    "model": response.model,  # Actual model used
    "usage": {
        "prompt_tokens": ...,
        "completion_tokens": ...,
        "total_tokens": ...,
    },
}
```

### Provider-Specific Metadata

#### OpenAI (GPT)

**Response Structure (2026):**
```python
response = {
    "id": "chatcmpl-...",
    "model": "gpt-5-mini",
    "choices": [{
        "message": {"role": "assistant", "content": "..."},
        "finish_reason": "stop",  # or "length", "content_filter"
    }],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
        "prompt_tokens_details": {
            "cached_tokens": 5,  # Important for cost optimization
        },
        "completion_tokens_details": {
            "reasoning_tokens": 15,  # For o1/o3 models
        },
    },
    "system_fingerprint": "fp_...",  # For reproducibility
}
```

**Extract:**
```python
metadata = {
    "model": response.model,
    "finish_reason": response.choices[0].finish_reason,
    "usage": {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "total_tokens": response.usage.total_tokens if response.usage else 0,
    },
}

# Optional: Add cached tokens if available
if response.usage and hasattr(response.usage, "prompt_tokens_details"):
    metadata["usage"]["cached_tokens"] = (
        response.usage.prompt_tokens_details.cached_tokens
    )

# Optional: Add reasoning tokens for o1/o3 models
if response.usage and hasattr(response.usage, "completion_tokens_details"):
    metadata["usage"]["reasoning_tokens"] = (
        response.usage.completion_tokens_details.reasoning_tokens
    )
```

#### Anthropic (Claude)

**Response Structure (2026):**
```python
response = {
    "id": "msg_...",
    "model": "claude-sonnet-4-5",
    "content": [{"type": "text", "text": "..."}],
    "stop_reason": "end_turn",  # or "max_tokens", "stop_sequence"
    "stop_sequence": None,
    "usage": {
        "input_tokens": 10,
        "output_tokens": 20,
    },
}
```

**Extract:**
```python
metadata = {
    "model": response.model,
    "stop_reason": response.stop_reason,
    "usage": {
        "prompt_tokens": response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
    },
}
```

#### Google (Gemini)

**Response Structure (2026):**
```python
response = {
    "text": "...",
    "usage_metadata": {
        "prompt_token_count": 10,
        "candidates_token_count": 20,
        "total_token_count": 30,
    },
    "candidates": [{
        "finish_reason": "STOP",  # or "MAX_TOKENS", "SAFETY"
        "safety_ratings": [...],  # Content filtering
    }],
}
```

**Extract:**
```python
metadata = {
    "model": model,  # Gemini doesn't return model in response
    "usage": {
        "prompt_tokens": (
            response.usage_metadata.prompt_token_count
            if hasattr(response, "usage_metadata")
            else 0
        ),
        "completion_tokens": (
            response.usage_metadata.candidates_token_count
            if hasattr(response, "usage_metadata")
            else 0
        ),
        "total_tokens": (
            response.usage_metadata.total_token_count
            if hasattr(response, "usage_metadata")
            else 0
        ),
    },
}
```

#### Mistral

Same as OpenAI (uses OpenAI-compatible API).

#### Grok (xAI)

**Response Structure (2026 - Enhanced):**
```python
response = {
    "model": "grok-4-fast",
    "usage": {
        "prompt_tokens": 37,
        "completion_tokens": 530,
        "total_tokens": 567,
        "prompt_tokens_details": {
            "text_tokens": 37,
            "audio_tokens": 0,
            "image_tokens": 0,
            "cached_tokens": 8,  # Cache hits
        },
        "completion_tokens_details": {
            "reasoning_tokens": 233,  # For reasoning models
            "audio_tokens": 0,
            "accepted_prediction_tokens": 0,
            "rejected_prediction_tokens": 0,
        },
        "num_sources_used": 0,  # For grounded responses
    },
}
```

**Extract (minimal):**
```python
metadata = {
    "model": response.model,
    "usage": {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "total_tokens": response.usage.total_tokens if response.usage else 0,
    },
}
```

#### DeepSeek

**CRITICAL: Reasoning Model Support**

DeepSeek R1 and reasoning models return a separate `reasoning_content` field:

```python
response = {
    "choices": [{
        "message": {
            "role": "assistant",
            "content": "The answer is...",  # Final answer
            "reasoning_content": "Let me think... Step 1..."  # Chain of thought
        }
    }],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 50,
        "total_tokens": 60,
        "completion_tokens_details": {
            "reasoning_tokens": 30,  # Tokens used in reasoning
        },
    },
}
```

**Extract:**
```python
# Get content
content = response.choices[0].message.content or ""

# IMPORTANT: Also extract reasoning_content if present
reasoning_content = getattr(response.choices[0].message, "reasoning_content", None)

metadata = {
    "model": response.model,
    "reasoning_content": reasoning_content,  # Store for display
    "usage": {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "total_tokens": response.usage.total_tokens if response.usage else 0,
    },
}

# Add reasoning tokens if available
if response.usage and hasattr(response.usage, "completion_tokens_details"):
    metadata["usage"]["reasoning_tokens"] = (
        response.usage.completion_tokens_details.reasoning_tokens
    )
```

**WARNING:** Do NOT pass `reasoning_content` back in subsequent API calls. It will cause a 400 error.

#### Perplexity

**CRITICAL: Citations Support**

Perplexity's main feature is web search with citations:

```python
response = {
    "choices": [{
        "message": {
            "role": "assistant",
            "content": "According to recent sources..."
        }
    }],
    "citations": [
        "https://example.com/article1",
        "https://example.com/article2"
    ],
    # or
    "search_results": [
        {"url": "https://...", "title": "...", "snippet": "..."},
    ],
    "usage": { ... },
}
```

**Extract:**
```python
metadata = {
    "model": response.model,
    "citations": getattr(response, "citations", None),  # URL sources
    "usage": {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "total_tokens": response.usage.total_tokens if response.usage else 0,
    },
}
```

---

## Provider-Specific Features

### DeepSeek: Reasoning Content

DeepSeek R1 models show their "thinking" process:

```python
async def get_full_response(self, ...):
    response = await self.client.chat.completions.create(...)

    content = response.choices[0].message.content or ""
    reasoning = getattr(response.choices[0].message, "reasoning_content", None)

    # Display reasoning if available
    if reasoning:
        print("\n[Reasoning Process]")
        print(reasoning)
        print("\n[Final Answer]")

    return content, metadata
```

### Perplexity: Citations

Display sources with the response:

```python
async def get_full_response(self, ...):
    response = await self.client.chat.completions.create(...)

    content = response.choices[0].message.content or ""
    citations = getattr(response, "citations", None)

    # Display citations if available
    if citations:
        print("\n[Sources]")
        for i, url in enumerate(citations, 1):
            print(f"  [{i}] {url}")

    return content, metadata
```

### Gemini: Safety Ratings

Check if content was filtered:

```python
async def get_full_response(self, ...):
    response = await self.client.aio.models.generate_content(...)

    # Check finish reason
    if hasattr(response, "candidates") and response.candidates:
        finish_reason = response.candidates[0].finish_reason
        if finish_reason == "SAFETY":
            print("[Warning] Response was filtered for safety")

    return content, metadata
```

---

## Testing Checklist

### Basic Functionality
- [ ] Send simple message and get response
- [ ] Stream response in real-time
- [ ] Handle empty messages
- [ ] Handle very long messages (test context limits)
- [ ] Multi-turn conversation works

### Error Handling
- [ ] Invalid API key returns clear error
- [ ] Network disconnection doesn't hang
- [ ] Timeout works (test with very long prompt if possible)
- [ ] Rate limit error shows appropriate message
- [ ] Server error (500) is handled gracefully

### Metadata
- [ ] Model name is extracted correctly
- [ ] Token usage is recorded
- [ ] Provider-specific fields work (citations, reasoning, etc.)

### Edge Cases
- [ ] Empty response from API
- [ ] Response with no content blocks
- [ ] Unicode and emoji in messages
- [ ] System prompt with special characters
- [ ] Consecutive same-role messages (for Perplexity)

---

## Implementation Priority

### Phase 1: Critical (Do First)
1. Add timeout support to all providers
2. Add basic error handling (try-except with logging)
3. Extract essential metadata (model, token usage)

### Phase 2: Nice-to-Have (If Needed)
1. Provider-specific features (citations, reasoning)
2. Detailed token breakdowns (cached, reasoning)
3. Retry logic with exponential backoff
4. Safety ratings and content filtering

---

## References

### Official Documentation (2026)

**OpenAI:**
- [Streaming API Reference](https://platform.openai.com/docs/api-reference/streaming)
- [Error Handling](https://platform.openai.com/docs/guides/error-codes)

**Anthropic (Claude):**
- [Messages API Streaming](https://docs.anthropic.com/en/api/messages-streaming)
- [Error Codes](https://docs.anthropic.com/en/api/errors)

**Google (Gemini):**
- [API Reference](https://ai.google.dev/api)
- [Rate Limits Guide](https://www.aifreeapi.com/en/posts/gemini-api-rate-limit-explained)

**Mistral:**
- [API Specifications](https://docs.mistral.ai/api)

**xAI (Grok):**
- [Rate Limits](https://docs.x.ai/docs/key-information/consumption-and-rate-limits)
- [Debugging Errors](https://docs.x.ai/docs/key-information/debugging)

**DeepSeek:**
- [Error Codes](https://api-docs.deepseek.com/quick_start/error_codes)
- [Reasoning Model](https://api-docs.deepseek.com/guides/reasoning_model)

**Perplexity:**
- [Error Handling 2025](https://4idiotz.com/tech/artificial-intelligence/perplexity-ai-api-error-handling-in-2025-best-practices-troubleshooting-guide/)
- [Structured Outputs](https://docs.perplexity.ai/guides/structured-outputs)

---

## Example: Complete Provider Template

Here's a complete provider template with all critical features:

```python
"""Example provider implementation with all critical features."""

from typing import AsyncIterator
import traceback


class ExampleProvider:
    """Example AI provider with proper error handling."""

    def __init__(self, api_key: str, timeout: float = 30.0):
        """Initialize provider.

        Args:
            api_key: API key
            timeout: Request timeout in seconds (0 = no timeout)
        """
        from openai import AsyncOpenAI

        timeout_value = timeout if timeout > 0 else None

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.example.com/v1",
            timeout=timeout_value,
        )
        self.api_key = api_key
        self.timeout = timeout

    def format_messages(self, conversation_messages: list[dict]) -> list[dict]:
        """Convert conversation format to provider format."""
        from ..message_formatter import lines_to_text

        formatted = []
        for msg in conversation_messages:
            content = lines_to_text(msg["content"])
            formatted.append({"role": msg["role"], "content": content})
        return formatted

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Send message with error handling and timeout."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            response = await self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                stream=stream,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            # Log error
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"\n[ERROR] {error_msg}")

            # Optional: Full traceback for debugging
            # traceback.print_exc()

            # Re-raise to let caller handle
            raise

    async def get_full_response(
        self, messages: list[dict], model: str, system_prompt: str | None = None
    ) -> tuple[str, dict]:
        """Get full response with complete metadata."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            response = await self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                stream=False,
            )

            content = response.choices[0].message.content or ""

            # Extract essential metadata
            metadata = {
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }

            return content, metadata

        except Exception as e:
            # Log error
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"\n[ERROR] {error_msg}")

            # Re-raise
            raise
```

---

## Summary

**Critical Features (Must Implement):**
1. ✅ **Timeout**: 30 seconds default, configurable via profile and /timeout command
2. ✅ **Error Handling**: Basic try-except with error logging
3. ✅ **Metadata**: Extract model name and token usage
4. ✅ **Error Logging**: Use `str(e)` or `traceback.format_exc()` for debugging

**Nice-to-Have (Implement If Needed):**
- Retry logic
- Provider-specific features (citations, reasoning)
- Detailed token breakdowns
- Safety ratings

**Philosophy:**
> Keep it simple. Focus on preventing hangs and crashes. Let users retry manually if needed.

