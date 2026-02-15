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
  /gpt                Switch to OpenAI GPT
  /gem                Switch to Google Gemini
  /cla                Switch to Anthropic Claude
  /grok               Switch to xAI Grok
  /perp               Switch to Perplexity
  /mist               Switch to Mistral
  /deep               Switch to DeepSeek

Model Management:
  /model              Show available models for current provider
  /model default      Restore to profile's default AI and model
  /model <query>      Switch model via exact/fuzzy match (auto-detects provider)
  /helper             Show current helper AI model
  /helper default     Restore to profile's default helper AI
  /helper <query>     Set helper via model query (exact/fuzzy)
  /helper <shortcut>  Set helper via provider shortcut (gpt/gem/cla/grok/perp/mist/deep)
                      Ambiguous matches prompt for numbered selection

Configuration:
  /input              Show current input mode
  /input quick        Enter sends, Alt/Option+Enter inserts newline (default)
  /input compose      Enter inserts newline, Alt/Option+Enter sends
  /input default      Restore to profile default input mode
  /timeout            Show current timeout setting
  /timeout default    Restore to profile's default timeout
  /timeout <secs>     Set timeout in seconds (0 = wait forever)
  /system             Show current system prompt path
  /system --          Remove system prompt from chat
  /system default     Restore profile default system prompt
  /system <persona>   Set system prompt by persona (e.g., razor, socrates)
  /system <path>      Set system prompt by path (~/ for home, @/ for app root)

Chat File Management:
  /new [name]         Create new chat file
  /open [name]        Open existing chat file (shows list if no name)
  /switch [name]      Switch chat (save current, then open selected chat)
  /close              Close current chat
  /rename             Select a chat and rename it
  /rename current <new_name>
                      Rename the current chat
  /rename <chat> <new_name>
                      Rename a specific chat by name/path
  /delete current     Delete the current chat (with confirmation)
  /delete [name]      Delete a chat file (shows list if no name)

Chat Control:
  /retry              Retry the last interaction (collect candidate responses)
                      Last interaction: user+assistant, user+error, or trailing error
  /apply              Apply latest retry candidate and exit retry mode
  /apply last         Apply latest retry candidate and exit retry mode
  /apply <hex_id>     Apply a specific retry candidate and exit retry mode
  /cancel             Abort retry and keep original response
  /secret             Show current secret mode state
  /secret on/off      Enable/disable secret mode explicitly
  /search             Show current search mode state
  /search on/off      Enable/disable web search
  /rewind             Delete the last full interaction (user+assistant/user+error), or trailing error
  /rewind last        Delete the last full interaction (user+assistant/user+error), or trailing error
  /rewind <hex_id>    Delete that message and all following messages
  /purge <hex_id>     Delete specific message(s) (breaks context!)
  /purge <id> <id>    Delete multiple messages

History:
  /history            Show last 10 messages
  /history all        Show all messages
  /history errors     Show only error messages
  /history <n>        Show last n messages
  /show <hex_id>      Show full content of specific message
  /status             Show current profile/chat/session status

Metadata:
  /title              Generate title using AI
  /title --           Clear title
  /title <text>       Set chat title
  /summary            Generate summary using AI
  /summary --         Clear summary
  /summary <text>     Set chat summary

Safety:
  /safe               Check entire chat for unsafe content
  /safe <hex_id>      Check specific message for unsafe content

Other:
  /help               Show this help
  /exit, /quit        Exit PolyChat"""

    async def exit_app(self, args: str) -> CommandResult:
        """Exit the application.

        Args:
            args: Not used

        Returns:
            Exit message (triggers exit in main loop)
        """
        return CommandSignal(kind="exit")
