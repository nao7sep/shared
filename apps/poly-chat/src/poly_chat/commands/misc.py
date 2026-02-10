"""Misc command mixin."""

from .types import CommandResult, CommandSignal


class MiscCommandsMixin:
    async def show_help(self, args: str) -> str:
        """Show help information.

        Args:
            args: Not used

        Returns:
            Help text
        """
        return """PolyChat Commands:

Provider Shortcuts:
  /gpt              Switch to OpenAI GPT
  /gem              Switch to Google Gemini
  /cla              Switch to Anthropic Claude
  /grok             Switch to xAI Grok
  /perp             Switch to Perplexity
  /mist             Switch to Mistral
  /deep             Switch to DeepSeek

Model Management:
  /model            Show available models for current provider
  /model <name>     Switch to specified model (auto-detects provider)
  /model default    Restore to profile's default AI and model
  /helper           Show current helper AI model
  /helper <model>   Set helper AI model (for background tasks)
  /helper default   Restore to profile's default helper AI

Configuration:
  /input            Show current input mode
  /input quick      Enter sends, Alt/Option+Enter inserts newline (default)
  /input compose    Enter inserts newline, Alt/Option+Enter sends
  /input default    Restore to profile default input mode
  /timeout          Show current timeout setting
  /timeout <secs>   Set timeout in seconds (0 = wait forever)
  /timeout default  Restore to profile's default timeout
  /system           Show current system prompt path
  /system <path>    Set system prompt (~/ for home, @/ for app root)
  /system --        Remove system prompt from chat
  /system default   Restore to profile's default system prompt

Chat File Management:
  /new [name]       Create new chat file
  /open [name]      Open existing chat file (shows list if no name)
  /switch [name]    Switch chat (save current, then open selected chat)
  /close            Close current chat
  /rename           Select a chat and rename it
  /rename current <new_name>
                    Rename the current chat
  /rename <chat> <new_name>
                    Rename a specific chat by name/path
  /delete current   Delete the current chat (with confirmation)
  /delete [name]    Delete a chat file (shows list if no name)

Chat Control:
  /retry            Enter retry mode (collect candidate responses)
  /apply <hex_id>   Apply one retry candidate and exit retry mode
  /cancel           Abort retry and keep original response
  /secret           Show current secret mode state
  /secret on/off    Enable/disable secret mode explicitly
  /search           Show current search mode state
  /search on/off    Enable/disable web search
  /thinking         Show current thinking mode state
  /thinking on/off  Enable/disable extended reasoning
  /rewind <hex_id>  Delete that message and all following messages
  /rewind turn      Delete the last full interaction (user+assistant/error)
  /rewind last      Delete only the last message
  /purge <hex_id>   Delete specific message(s) (breaks context!)
  /purge <id> <id>  Delete multiple messages

History:
  /history          Show last 10 messages
  /history <n>      Show last n messages
  /history all      Show all messages
  /history --errors Show only error messages
  /show <hex_id>    Show full content of specific message
  /status           Show current profile/chat/session status

Metadata:
  /title            Generate title using AI
  /title <text>     Set chat title
  /title --         Clear title
  /summary          Generate summary using AI
  /summary <text>   Set chat summary
  /summary --       Clear summary

Safety:
  /safe             Check entire chat for unsafe content
  /safe <hex_id>    Check specific message for unsafe content

Other:
  /help             Show this help
  /exit, /quit      Exit PolyChat

Note: Use '--' to delete/clear values (e.g., /title --, /summary --)"""

    async def exit_app(self, args: str) -> CommandResult:
        """Exit the application.

        Args:
            args: Not used

        Returns:
            Exit message (triggers exit in main loop)
        """
        return CommandSignal(kind="exit")
