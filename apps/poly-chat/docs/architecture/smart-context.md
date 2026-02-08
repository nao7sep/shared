# Smart Context Architecture

**Status:** Future Feature - Architecture Only
**Date:** 2026-02-07

## Overview

Smart Context is a proposed feature to enable super-long chat sessions (1000+ interactions over months/years) by generating context-aware summaries for efficient retrieval and context window management.

## Problem Statement

### Current Limitations

1. **Context Window Limits**: AI models have finite context windows
2. **Long Chats**: Users may want continuous conversations over extended periods
3. **Context Loss**: Simply truncating old messages loses important context
4. **Naive Summarization**: Summarizing messages in isolation loses conversational flow

### Goal

Enable indefinite chat length while maintaining coherent conversation context through intelligent, context-aware summarization.

## Proposed Solution

### Context-Aware Summarization

Instead of summarizing messages in isolation, generate summaries that preserve conversational flow:

#### For User Messages
Summarize with awareness of what came before and what response followed:
- Input: [Previous Assistant Message] + [User Message] + [Following Assistant Message]
- Prompt: "Summarize this user message so that the transition from [prev] to [this] to [next] is natural"
- Result: Summary that preserves conversational flow

#### For Assistant Messages
Summarize with awareness of the question asked and follow-up:
- Input: [Previous User Message] + [Assistant Message] + [Following User Message]
- Prompt: "Summarize this assistant response so [prev question] and [next question] connect naturally via this summary"
- Result: Summary that preserves context thread

### Summary Generation Algorithm

```python
def generate_smart_summary(messages: list, index: int, helper_ai):
    """Generate context-aware summary for message at index."""
    msg = messages[index]

    # Get surrounding context
    prev_msg = messages[index - 1] if index > 0 else None
    next_msg = messages[index + 1] if index < len(messages) - 1 else None

    # Build context-aware prompt
    context_parts = []
    if prev_msg:
        context_parts.append(f"Previous: {prev_msg['content']}")
    context_parts.append(f"Current: {msg['content']}")
    if next_msg:
        context_parts.append(f"Next: {next_msg['content']}")

    prompt = f"""Summarize the 'Current' message so that the conversational
flow from Previous → Current → Next is preserved. The summary should:
1. Capture the key information
2. Maintain natural transitions
3. Be much shorter than the original (aim for 20-30% of original length)

{chr(10).join(context_parts)}

Summary:"""

    summary = invoke_helper_ai(helper_ai, prompt)

    return {
        "summary": summary,
        "summary_model": helper_ai,
        "summary_at": datetime.now().isoformat()
    }
```

## Message Schema Extension

### Current Schema
```json
{
  "timestamp": "2026-02-02T00:00:00+00:00",
  "role": "user",
  "content": ["Message text here"],
  "model": "claude-haiku-4-5"
}
```

### Extended Schema (Future)
```json
{
  "timestamp": "2026-02-02T00:00:00+00:00",
  "role": "user",
  "content": ["Message text here"],
  "model": "claude-haiku-4-5",

  // Smart Context fields (optional, generated on-demand)
  "summary": "Brief context-aware summary",
  "summary_model": "claude-haiku-4-5",
  "summary_at": "2026-02-03T00:00:00+00:00"
}
```

**Key Design Decisions:**
- Fields are **optional** - messages work without them
- Summaries are **regenerable** - not source of truth
- Summaries are **lazy** - generated when needed, not immediately

## Storage Strategies

### Option 1: Inline in Chat File (Simplest)
Store summaries directly in chat JSON file.

**Pros:**
- Simple implementation
- Single source of truth
- Easy backup/migration

**Cons:**
- Increases file size
- Slower loading for large chats

### Option 2: Separate Summary File (Recommended)
Store summaries in parallel file: `chat-name.summaries.json`

**Pros:**
- Fast chat loading (summaries loaded on-demand)
- Summaries can be regenerated without affecting chat
- Clear separation of concerns

**Cons:**
- Two files to manage
- Sync complexity

### Option 3: SQLite Database (Most Scalable)
Store summaries in SQLite with vector embeddings.

**Pros:**
- Efficient querying
- Support for vector search (RAG)
- Handles thousands of messages easily

**Cons:**
- Added complexity
- Requires SQLite dependency

**Recommendation:** Start with Option 2, migrate to Option 3 if needed.

## Context Window Management

### Strategy: Hierarchical Summarization

1. **Recent Messages** (last 10-20): Use full content
2. **Middle History** (21-100): Use summaries
3. **Old History** (100+): Use aggregated summaries or omit

### Example Context Assembly
For a chat with 500 messages, sending to AI:
```
System Prompt
+ Aggregated Summary (messages 1-450): "This conversation covers..."
+ Individual Summaries (messages 451-490): [40 summaries]
+ Full Content (messages 491-500): [10 recent messages]
+ User's New Message
```

This keeps context window manageable while preserving key information.

## Implementation Phases

### Phase 1: Schema Preparation (Optional)
- ✓ Message schema already supports arbitrary fields
- ✓ Chat loading/saving handles unknown fields gracefully
- No changes needed - schema is already extensible

### Phase 2: Summary Generation (Future)
- Implement context-aware summarization
- Add `/summarize-all` command
- Use helper AI for generation

### Phase 3: Context Assembly (Future)
- Implement hierarchical context building
- Modify message sending to use summaries when needed
- Add configuration for context window thresholds

### Phase 4: Advanced Features (Future)
- Vector embeddings for RAG
- Semantic search across chat history
- Smart retrieval of relevant old messages

## Commands (Future)

Potential commands to implement:

```
/summarize-all          Generate summaries for all messages
/summarize-from <id>    Generate summaries from hex ID onwards
/clear-summaries        Delete all summaries (forces regeneration)
/context-stats          Show context usage statistics
```

## Performance Considerations

### Summary Generation Cost
- Assume 200 tokens per message to summarize
- Assume 60 tokens per summary generated
- For 1000 messages: ~260,000 tokens (one-time cost)
- Using cheap models (haiku/gpt-5-mini): ~$0.30 total

### Storage Cost
- Original message: ~500 bytes
- Summary: ~150 bytes
- For 1000 messages: ~650KB total (negligible)

### Retrieval Speed
- With indexed summaries: O(log n)
- With vector search: O(k) where k = top results
- Both are fast enough for real-time use

## Security Considerations

### Privacy
- Summaries may inadvertently preserve sensitive info
- Running `/safe` should check both content AND summaries
- Consider excluding sensitive messages from summarization

### Regeneration
- Users must be able to regenerate summaries
- Changes to summarization algorithm should allow bulk regeneration
- Summaries should include version number for compatibility

## Future Enhancements

### Vector Embeddings (RAG)
```json
{
  "summary": "...",
  "embedding": [0.1, 0.2, ...],  // 1536 dimensions
  "embedding_model": "text-embedding-3-small"
}
```

Benefits:
- Semantic search across history
- Smart retrieval of relevant context
- Answer questions about past conversations

### Automatic Pruning
- Detect messages that can be safely summarized
- Automatic background summarization
- User-configurable thresholds

### Multi-level Summaries
- Level 1: Individual message summaries
- Level 2: Conversation segment summaries (10 messages)
- Level 3: Topic summaries (50+ messages)

Enables efficient context at any scale.

## Migration Path

### From Current to Smart Context

1. **No breaking changes** - summaries are optional
2. **Gradual adoption** - summarize old chats incrementally
3. **Backward compatible** - old chats work without summaries
4. **Forward compatible** - new schema handles future fields

Existing chats require zero changes to work with Smart Context.

## References

- RAG (Retrieval-Augmented Generation)
- Hierarchical summarization techniques
- Vector embeddings for semantic search
- Long-context management strategies

## Conclusion

Smart Context enables PolyChat to scale from short conversations to multi-year, thousand-message chats without losing coherence or hitting context limits.

**Current Status:** Architecture documented, ready for future implementation.
**Next Steps:** None - wait for user request before implementing.
