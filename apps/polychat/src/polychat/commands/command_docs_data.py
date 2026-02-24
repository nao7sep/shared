"""Command documentation metadata constants."""

from __future__ import annotations

try:  # pragma: no cover - fallback used by standalone doc generator script
    from .command_docs_models import CommandDocEntry, CommandDocSection
except ImportError:  # pragma: no cover
    from command_docs_models import CommandDocEntry, CommandDocSection  # type: ignore[import-not-found,no-redef]


COMMAND_DOC_SECTIONS: tuple[CommandDocSection, ...] = (
    CommandDocSection(
        title="Provider Shortcuts",
        entries=(
            CommandDocEntry(("gpt",), "/gpt", "Switch to OpenAI GPT", "/gpt", "Switch to OpenAI GPT"),
            CommandDocEntry(("gem",), "/gem", "Switch to Google Gemini", "/gem", "Switch to Google Gemini"),
            CommandDocEntry(("cla",), "/cla", "Switch to Anthropic Claude", "/cla", "Switch to Anthropic Claude"),
            CommandDocEntry(("grok",), "/grok", "Switch to xAI Grok", "/grok", "Switch to xAI Grok"),
            CommandDocEntry(("perp",), "/perp", "Switch to Perplexity", "/perp", "Switch to Perplexity"),
            CommandDocEntry(("mist",), "/mist", "Switch to Mistral", "/mist", "Switch to Mistral"),
            CommandDocEntry(("deep",), "/deep", "Switch to DeepSeek", "/deep", "Switch to DeepSeek"),
        ),
    ),
    CommandDocSection(
        title="Model Management",
        entries=(
            CommandDocEntry(
                ("model",),
                "/model",
                "Show available models for current provider",
                "/model",
                "Show available models for current provider",
            ),
            CommandDocEntry(
                ("model",),
                "/model <query>",
                "Switch model via exact or fuzzy match (provider auto-detected)",
                "/model <query>",
                "Switch model via exact or fuzzy match (provider auto-detected)",
            ),
            CommandDocEntry(
                ("model",),
                "/model default",
                "Restore profile default AI and model",
                "/model default",
                "Restore profile default AI and model",
            ),
            CommandDocEntry(
                ("helper",),
                "/helper",
                "Show current helper AI model",
                "/helper",
                "Show current helper AI model",
            ),
            CommandDocEntry(
                ("helper",),
                "/helper <query>",
                "Set helper AI model via exact or fuzzy match",
                "/helper <query>",
                "Set helper AI model via exact or fuzzy match",
            ),
            CommandDocEntry(
                ("helper",),
                "/helper <shortcut>",
                "Set helper from provider shortcut (gpt/gem/cla/grok/perp/mist/deep)",
                "/helper <shortcut>",
                "Set helper from provider shortcut (`gpt`, `gem`, `cla`, `grok`, `perp`, `mist`, `deep`)",
                help_continuations=("Ambiguous matches prompt for numbered selection",),
            ),
            CommandDocEntry(
                ("helper",),
                "/helper default",
                "Restore helper AI from profile default",
                "/helper default",
                "Restore helper AI from profile default",
            ),
        ),
    ),
    CommandDocSection(
        title="Configuration",
        entries=(
            CommandDocEntry(("input",), "/input", "Show current input mode", "/input", "Show current input mode"),
            CommandDocEntry(
                ("input",),
                "/input quick",
                "Enter sends, Option/Alt+Enter inserts newline",
                "/input quick",
                "Enter sends, Option/Alt+Enter inserts newline",
            ),
            CommandDocEntry(
                ("input",),
                "/input compose",
                "Enter inserts newline, Option/Alt+Enter sends",
                "/input compose",
                "Enter inserts newline, Option/Alt+Enter sends",
            ),
            CommandDocEntry(
                ("input",),
                "/input default",
                "Restore profile default input mode",
                "/input default",
                "Restore profile default input mode",
            ),
            CommandDocEntry(
                ("timeout",),
                "/timeout",
                "Show current timeout setting",
                "/timeout",
                "Show current timeout setting",
            ),
            CommandDocEntry(
                ("timeout",),
                "/timeout default",
                "Restore profile default timeout",
                "/timeout default",
                "Restore profile default timeout",
            ),
            CommandDocEntry(
                ("timeout",),
                "/timeout <secs>",
                "Set timeout (0 = wait forever)",
                "/timeout <secs>",
                "Set timeout (0 = wait forever)",
            ),
            CommandDocEntry(
                ("system",),
                "/system",
                "Show current system prompt path",
                "/system",
                "Show current system prompt path",
            ),
            CommandDocEntry(
                ("system",),
                "/system --",
                "Remove system prompt from chat",
                "/system --",
                "Remove system prompt from chat",
            ),
            CommandDocEntry(
                ("system",),
                "/system default",
                "Restore profile default system prompt",
                "/system default",
                "Restore profile default system prompt",
            ),
            CommandDocEntry(
                ("system",),
                "/system <persona>",
                "Set system prompt by persona (e.g., razor, socrates)",
                "/system <persona>",
                "Set system prompt by persona (e.g., `razor`, `socrates`)",
            ),
            CommandDocEntry(
                ("system",),
                "/system <path>",
                "Set system prompt by path",
                "/system <path>",
                "Set system prompt by path",
            ),
        ),
    ),
    CommandDocSection(
        title="Chat File Management",
        entries=(
            CommandDocEntry(
                ("new",),
                "/new",
                "Create new chat with timestamped filename",
                "/new",
                "Create new chat with timestamped filename",
            ),
            CommandDocEntry(
                ("new",),
                "/new <name>",
                "Create new chat with provided name",
                "/new <name>",
                "Create new chat with the provided name",
            ),
            CommandDocEntry(("open",), "/open", "Select from list of chats", "/open", "Select from list of chats"),
            CommandDocEntry(
                ("open",),
                "/open <path>",
                "Open specific chat file",
                "/open <path>",
                "Open specific chat file",
            ),
            CommandDocEntry(
                ("switch",),
                "/switch",
                "Switch chats (save current, then select chat to open)",
                "/switch",
                "Switch chats (save current, then select chat to open)",
            ),
            CommandDocEntry(
                ("switch",),
                "/switch <path>",
                "Switch to specific chat file",
                "/switch <path>",
                "Switch to specific chat file",
            ),
            CommandDocEntry(("close",), "/close", "Close current chat", "/close", "Close current chat"),
            CommandDocEntry(
                ("rename",),
                "/rename",
                "Select chat to rename",
                "/rename",
                "Select chat to rename",
            ),
            CommandDocEntry(
                ("rename",),
                "/rename current <new-name>",
                "Rename current chat",
                "/rename current <new-name>",
                "Rename current chat",
            ),
            CommandDocEntry(
                ("rename",),
                "/rename <chat> <new-name>",
                "Rename specific chat by name/path",
                "/rename <chat> <new-name>",
                "Rename specific chat by name/path",
            ),
            CommandDocEntry(
                ("delete",),
                "/delete",
                "Select chat to delete",
                "/delete",
                "Select chat to delete",
            ),
            CommandDocEntry(
                ("delete",),
                "/delete current",
                "Delete current chat",
                "/delete current",
                "Delete current chat",
            ),
            CommandDocEntry(
                ("delete",),
                "/delete <path>",
                "Delete specific chat file",
                "/delete <path>",
                "Delete specific chat file",
            ),
        ),
    ),
    CommandDocSection(
        title="Chat Control",
        entries=(
            CommandDocEntry(
                ("retry",),
                "/retry",
                "Retry last interaction and generate candidate responses",
                "/retry",
                "Retry the last interaction and generate candidate responses",
            ),
            CommandDocEntry(
                ("apply",),
                "/apply",
                "Apply latest retry candidate and exit retry mode",
                "/apply",
                "Apply latest retry candidate and exit retry mode",
            ),
            CommandDocEntry(
                ("apply",),
                "/apply last",
                "Apply latest retry candidate and exit retry mode",
                "/apply last",
                "Apply latest retry candidate and exit retry mode",
            ),
            CommandDocEntry(
                ("apply",),
                "/apply <hex_id>",
                "Apply one retry candidate by ID and exit retry mode",
                "/apply <hex_id>",
                "Apply one retry candidate by ID and exit retry mode",
            ),
            CommandDocEntry(
                ("cancel",),
                "/cancel",
                "Abort retry and keep original response",
                "/cancel",
                "Abort retry and keep original response",
            ),
            CommandDocEntry(
                ("secret",),
                "/secret",
                "Show current secret mode state",
                "/secret",
                "Show current secret mode state",
            ),
            CommandDocEntry(
                ("secret",),
                "/secret on/off",
                "Explicitly enable/disable secret mode",
                "/secret on/off",
                "Explicitly enable/disable secret mode",
            ),
            CommandDocEntry(
                ("search",),
                "/search",
                "Show current search mode state and supported providers",
                "/search",
                "Show current search mode state and supported providers",
            ),
            CommandDocEntry(
                ("search",),
                "/search on/off",
                "Enable/disable web search with inline citations",
                "/search on/off",
                "Enable/disable web search with inline citations",
            ),
            CommandDocEntry(
                ("rewind",),
                "/rewind",
                "Delete last full interaction (user+assistant/user+error), or trailing error",
                "/rewind",
                "Delete last full interaction (user+assistant/user+error), or trailing error",
            ),
            CommandDocEntry(
                ("rewind",),
                "/rewind last",
                "Delete last full interaction (user+assistant/user+error), or trailing error",
                "/rewind last",
                "Delete the last full interaction (user+assistant/user+error), or trailing error",
            ),
            CommandDocEntry(
                ("rewind",),
                "/rewind <hex_id>",
                "Delete that message and all following messages",
                "/rewind <hex_id>",
                "Delete that message and all following messages",
            ),
            CommandDocEntry(
                ("purge",),
                "/purge <hex_id> [hex_id2 ...]",
                "Delete specific messages (breaks context)",
                "/purge <hex_id> [hex_id2 ...]",
                "Delete specific messages (breaks context)",
            ),
        ),
    ),
    CommandDocSection(
        title="History",
        entries=(
            CommandDocEntry(("history",), "/history", "Show last 10 messages", "/history", "Show last 10 messages"),
            CommandDocEntry(
                ("history",),
                "/history all",
                "Show all messages",
                "/history all",
                "Show all messages",
            ),
            CommandDocEntry(
                ("history",),
                "/history errors",
                "Show only error messages",
                "/history errors",
                "Show error messages only",
            ),
            CommandDocEntry(
                ("history",),
                "/history <n>",
                "Show last n messages",
                "/history <n>",
                "Show last n messages",
            ),
            CommandDocEntry(
                ("show",),
                "/show <hex_id>",
                "Show full content of one message",
                "/show <hex_id>",
                "Show full content of one message",
            ),
            CommandDocEntry(
                ("status",),
                "/status",
                "Show current profile/chat/session status",
                "/status",
                "Show current profile/chat/session status",
            ),
        ),
    ),
    CommandDocSection(
        title="Metadata",
        entries=(
            CommandDocEntry(("title",), "/title", "Generate title using AI", "/title", "Generate title using AI"),
            CommandDocEntry(("title",), "/title --", "Clear title", "/title --", "Clear title"),
            CommandDocEntry(("title",), "/title <text>", "Set chat title", "/title <text>", "Set chat title"),
            CommandDocEntry(
                ("summary",),
                "/summary",
                "Generate summary using AI",
                "/summary",
                "Generate summary using AI",
            ),
            CommandDocEntry(("summary",), "/summary --", "Clear summary", "/summary --", "Clear summary"),
            CommandDocEntry(
                ("summary",),
                "/summary <text>",
                "Set chat summary",
                "/summary <text>",
                "Set chat summary",
            ),
        ),
    ),
    CommandDocSection(
        title="Safety",
        entries=(
            CommandDocEntry(
                ("safe",),
                "/safe",
                "Check entire chat for unsafe content",
                "/safe",
                "Check entire chat for unsafe content",
            ),
            CommandDocEntry(
                ("safe",),
                "/safe <hex_id>",
                "Check one message for unsafe content",
                "/safe <hex_id>",
                "Check one message for unsafe content",
            ),
        ),
    ),
    CommandDocSection(
        title="Other",
        entries=(
            CommandDocEntry(("help",), "/help", "Show all commands", "/help", "Show all commands"),
            CommandDocEntry(
                ("exit", "quit"),
                "/exit, /quit",
                "Exit PolyChat",
                "/exit` or `/quit",
                "Exit PolyChat",
            ),
        ),
    ),
)


README_CHAT_FILE_NOTE = "Delete operations always ask for confirmation and require typing `yes`."

README_LAST_INTERACTION_BLOCK = "\n".join(
    [
        '**What "Last Interaction" Means:**',
        "PolyChat defines the last interaction as one of:",
        "1. A trailing `user + assistant` pair",
        "2. A trailing `user + error` pair",
        "3. A standalone trailing `error`",
        "",
        "`/retry` retries the last interaction. `/rewind` and `/rewind last` delete the last interaction.",
    ]
)

README_COMMANDS_FOOTER = "\n".join(
    [
        'When commands show chat lists for selection (`/open`, `/switch`, `/rename`, `/delete`), "Last Updated" is shown in your local time.',
        "For `/model` and `/helper`, fuzzy matching normalizes names to alphanumeric characters and uses in-order subsequence matching (for example, `op4` or `o4.6` can match `claude-opus-4-6`). When multiple models match, PolyChat prompts you to choose by number.",
    ]
)
