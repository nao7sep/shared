## Logging Safety Policy

This project treats logs as local diagnostics, not as a place to store raw user or provider data.

Safe to include:
- provider, model, mode, task, and command names
- elapsed time, token counts, cost estimates, and message counts
- chat/profile/log file paths
- HTTP method, status, reason, and sanitized URL
- exception type and sanitized exception text
- internal stack traces for application logic failures

Do not include:
- raw chat messages, prompts, summaries, or system prompts
- raw request or response bodies from AI providers
- API keys, bearer tokens, JWTs, cookies, or auth headers
- raw provider/auth/network exception dumps when they may contain secrets

Rules:
- Prefer structured metadata over content.
- Sanitize provider, auth, and transport errors before logging or surfacing them.
- Keep tracebacks only for internal application failures where the stack is useful and does not expose provider payloads.
