# AI Provider Tests

## Quick Start

### 1. Configure API Keys

Fill in `__TEST_API_KEYS.json` at repo root (or any parent directory):

```json
{
  "openai": {
    "api_key": "sk-...",
    "model": "gpt-4o-mini"
  },
  "claude": {
    "api_key": "sk-ant-...",
    "model": "claude-3-5-sonnet-20241022"
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

The end-to-end test validates the **complete application flow**:

1. **Creates temporary profile** with your API keys from `__TEST_API_KEYS.json`
2. **Sends messages to each available AI** (rotating through providers)
3. **Saves conversation** to JSON file
4. **Loads conversation** in a new session (simulating app restart)
5. **Verifies data integrity**:
   - Message count matches
   - All message data preserved exactly
   - Asks AI to count interactions (validates AI can read the log)

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
[10:30:15.249]     User message: Say hello and tell me your name.
[10:30:16.892]     Response (1.64s): Hello! I'm ChatGPT, an AI assistant created by OpenAI...

[10:30:16.893]   Testing CLAUDE...
[10:30:16.893]     User message: What is 2 + 2? Answer with just the number.
[10:30:18.234]     Response (1.34s): 4

[10:30:18.235] Completed 2 successful interaction(s) in 2.98s total

[10:30:18.236] PHASE 3: Saving conversation
[10:30:18.236] --------------------------------------------------------------------------------
[10:30:18.239]   Saved to: /tmp/xyz/conversations/e2e-test.json
[10:30:18.239]   Save time: 0.003s
[10:30:18.239]   Total messages: 4
[10:30:18.240]   File size: 1,234 bytes

[10:30:18.240] PHASE 4: Loading conversation (simulating new session)
[10:30:18.240] --------------------------------------------------------------------------------
[10:30:18.242]   Loaded from: /tmp/xyz/conversations/e2e-test.json
[10:30:18.242]   Load time: 0.002s
[10:30:18.242]   Messages loaded: 4

[10:30:18.243] PHASE 5: Verifying data integrity
[10:30:18.243] --------------------------------------------------------------------------------
[10:30:18.243]   Original message count: 4
[10:30:18.243]   Loaded message count: 4
[10:30:18.243]   ✓ Message count matches
[10:30:18.244]   ✓ All message data matches exactly

[10:30:18.244] PHASE 6: AI-based verification (ask AI to count interactions)
[10:30:18.244] --------------------------------------------------------------------------------
[10:30:18.245]   Using openai for verification
[10:30:18.245]   Verification prompt: Count the number of user messages...
[10:30:19.567]   AI response (1.32s): 3
[10:30:19.567]   AI reported: 3 user messages
[10:30:19.567]   Actual count: 3 user messages
[10:30:19.567]   ✓ AI verification successful!

[10:30:19.568] ================================================================================
[10:30:19.568] TEST SUMMARY
[10:30:19.568] ================================================================================
[10:30:19.568] ✓ Tested 2 AI provider(s)
[10:30:19.568] ✓ Successful interactions: 2
[10:30:19.568] ✓ Total messages in conversation: 5
[10:30:19.568] ✓ Conversation saved and loaded successfully
[10:30:19.568] ✓ Data integrity verified
[10:30:19.568] ✓ Total test time: 4.33s
[10:30:19.568] ================================================================================
[10:30:19.568] END-TO-END TEST PASSED
[10:30:19.568] ================================================================================
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

## Cost Estimate

Each test run sends ~3-5 short messages to each configured AI:
- OpenAI (gpt-4o-mini): ~$0.001-0.005
- Claude (sonnet): ~$0.01-0.03
- Gemini (flash): ~$0.0001-0.001
- Others: varies

**Total per run: ~$0.01-0.05** depending on which AIs you have configured.

## Next Steps

Once the E2E test passes:
1. You can confidently test the actual CLI app
2. Add more AI providers
3. Test advanced features (retry, time travel, etc.)
4. The foundation is solid
