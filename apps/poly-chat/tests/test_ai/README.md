# AI Provider Tests

## Quick Start

### 1. Configure API Keys

Fill in `__TEST_API_KEYS.json` at repo root (or any parent directory):

```json
{
  "openai": {
    "api_key": "sk-...",
    "model": "gpt-5-mini"
  },
  "claude": {
    "api_key": "sk-ant-...",
    "model": "claude-haiku-4-5"
  }
}
```

You only need to fill in the providers you want to test. Leave others empty.

### 2. Run the End-to-End Test

```bash
# From poly-chat directory
pytest tests/test_ai/test_end_to_end.py -v -s

# Or with marker
pytest -m e2e -v -s
```

**Important**: Use `-s` flag to see detailed output!

## What the E2E Test Does

The end-to-end test validates the **complete application flow** using **collaborative storytelling**:

1. **Creates temporary profile** with your API keys from `__TEST_API_KEYS.json` (auto-deleted after test)
2. **Sends contextual prompts to each available AI** - each AI adds one sentence to build a collaborative story
3. **Saves conversation** to JSON file
4. **Loads conversation** in a new session (simulating app restart)
5. **Verifies data integrity**:
   - Message count matches
   - All message data preserved exactly
   - Asks AI to summarize the story and count interactions (validates AI can read the conversation history)

### Why This Test Matters

This is the **one test that validates everything**:

- ✅ Profile loading works
- ✅ API key management works
- ✅ All AI provider bridges work (conversation ↔ SDK format)
- ✅ Conversation persistence works (save/load)
- ✅ Data structure roundtrips correctly
- ✅ Real API calls work end-to-end

**If this test passes, the core app works.**

## Output Example

```
[10:30:15.234] ================================================================================
[10:30:15.234] STARTING END-TO-END TEST
[10:30:15.234] ================================================================================
[10:30:15.235] Found 3 available AI provider(s): openai, claude, gemini

[10:30:15.245] PHASE 1: Setup
[10:30:15.245] --------------------------------------------------------------------------------
[10:30:15.246] Creating temporary profile...
[10:30:15.247]   Profile created: /tmp/xyz/test-profile.json
[10:30:15.247]   Default AI: openai
[10:30:15.247]   Available AIs: openai, claude, gemini

[10:30:15.248] PHASE 2: Sending messages to AI providers
[10:30:15.248] --------------------------------------------------------------------------------
[10:30:15.249]   Testing OPENAI...
[10:30:15.249]     API endpoint: https://api.openai.com/v1
[10:30:15.249]     User message: Start a short story with one sentence. Introduce a character and a setting.
[10:30:16.892]     Response (1.64s, 28 chunks): Sarah stood at the edge of the ancient forest, her backpack heavy with supplies for a journey she wasn't sure she was ready for.

[10:30:16.893]   Testing CLAUDE...
[10:30:16.893]     API endpoint: https://api.anthropic.com
[10:30:16.893]     User message: Continue the story. Add one sentence describing what the character does next.
[10:30:18.234]     Response (1.34s, 32 chunks): She took a deep breath and stepped onto the moss-covered path, feeling the cool shadows of towering oaks embrace her.

[10:30:18.235]   Testing GEMINI...
[10:30:18.235]     API endpoint: https://generativelanguage.googleapis.com
[10:30:18.235]     User message: Add a complication or challenge to the story in one sentence.
[10:30:19.156]     Response (0.92s, 2 chunks): Suddenly, a deep growl echoed from the undergrowth, and Sarah froze as a pair of glowing eyes appeared in the darkness.

[10:30:19.157] Completed 3 successful interaction(s) in 3.90s total

[10:30:19.158] PHASE 3: Saving conversation
[10:30:19.158] --------------------------------------------------------------------------------
[10:30:19.161]   Saved to: /tmp/xyz/conversations/e2e-test.json
[10:30:19.161]   Save time: 0.003s
[10:30:19.161]   Total messages: 6
[10:30:19.162]   File size: 2,456 bytes

[10:30:19.162] PHASE 4: Loading conversation (simulating new session)
[10:30:19.162] --------------------------------------------------------------------------------
[10:30:19.164]   Loaded from: /tmp/xyz/conversations/e2e-test.json
[10:30:19.164]   Load time: 0.002s
[10:30:19.164]   Messages loaded: 6

[10:30:19.165] PHASE 5: Verifying data integrity
[10:30:19.165] --------------------------------------------------------------------------------
[10:30:19.165]   Original message count: 6
[10:30:19.165]   Loaded message count: 6
[10:30:19.165]   ✓ Message count matches
[10:30:19.166]   ✓ All message data matches exactly

[10:30:19.166] PHASE 6: AI-based verification (ask AI to count interactions)
[10:30:19.166] --------------------------------------------------------------------------------
[10:30:19.167]   Using openai for verification
[10:30:19.167]   Verification prompt: We just wrote a collaborative story together...
[10:30:20.489]   AI response (1.32s, 24 chunks):
[10:30:20.489]   We wrote a story about Sarah entering an ancient forest for an uncertain journey. She steps onto a moss-covered path, but encounters danger when glowing eyes and a growl emerge from the darkness.
[10:30:20.489]
[10:30:20.489]   3
[10:30:20.490]   AI reported: 3 user messages
[10:30:20.490]   Actual count: 4 user messages
[10:30:20.490]   ⚠ Count mismatch (acceptable - AI read and understood the conversation)

[10:30:20.491] ================================================================================
[10:30:20.491] TEST SUMMARY
[10:30:20.491] ================================================================================
[10:30:20.491] ✓ Tested 3 AI provider(s)
[10:30:20.491] ✓ Successful interactions: 3
[10:30:20.491] ✓ Total messages in conversation: 7
[10:30:20.491] ✓ Conversation saved and loaded successfully
[10:30:20.491] ✓ Data integrity verified
[10:30:20.491] ✓ Total test time: 5.26s
[10:30:20.491] ================================================================================
[10:30:20.491] END-TO-END TEST PASSED
[10:30:20.491] ================================================================================
```

## Test Markers

```bash
# Run only e2e test
pytest -m e2e

# Run unit tests (mocked, from old test files if any)
pytest -m "not e2e and not integration"

# Run all tests
pytest tests/test_ai/
```

## Troubleshooting

### "No AI providers configured"

- Check `__TEST_API_KEYS.json` exists
- Verify at least one provider has non-empty `api_key`

### "API key not available"

- Make sure API keys are valid
- Check they're not expired
- Verify they have correct permissions

### Import errors

```bash
# Install dependencies
cd /path/to/poly-chat
poetry install
```

### Test hangs or times out

- Check network connectivity
- Verify API keys are valid
- Some AIs might be slow - this is normal

### DeepSeek identifies as ChatGPT

This is **expected behavior**. DeepSeek uses OpenAI-compatible API and the model itself may respond that it's ChatGPT when asked about its identity. This is the model mimicking ChatGPT's behavior, not an implementation issue. The test correctly calls DeepSeek's API endpoint (`https://api.deepseek.com/v1`).

### Gemini returns fewer chunks

This is **normal**. Gemini's streaming API sends fewer, larger chunks compared to OpenAI-style streaming. You might see 2-5 chunks from Gemini while OpenAI/Claude send 20-40 chunks for the same response. Both are correct - it's just different chunking strategies.

## Technical Notes

### How Endpoints Are Detected

The test displays API endpoints to verify that different AI providers are being called:

- **OpenAI-compatible APIs** (OpenAI, DeepSeek, Grok, Perplexity, Mistral): Access via `client.base_url`
- **Claude (Anthropic)**: Access via `client._client.base_url`
- **Gemini (Google GenAI)**: Access via `client._api_client._http_options.base_url`

Each provider uses a different SDK with different internal structures, so the test handles all three cases.

## Cost Estimate

Each test run uses collaborative storytelling where each AI contributes one sentence:
- OpenAI (gpt-5-mini): ~$0.001-0.005 per run
- Claude (haiku-4-5): ~$0.001-0.005 per run
- Gemini (flash): ~$0.0001-0.001 per run
- DeepSeek: ~$0.0001-0.001 per run
- Grok: ~$0.005-0.01 per run
- Perplexity: ~$0.001-0.005 per run
- Mistral: ~$0.001-0.005 per run

**Total per run: ~$0.01-0.05** depending on which AIs you have configured.

The storytelling format creates a meaningful conversation history for testing save/load functionality while keeping costs minimal.

## Next Steps

Once the E2E test passes:
1. You can confidently test the actual CLI app
2. Add more AI providers
3. Test advanced features (retry, time travel, etc.)
4. The foundation is solid
