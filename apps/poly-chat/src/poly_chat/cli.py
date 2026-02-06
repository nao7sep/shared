"""CLI entry point and REPL loop for PolyChat."""

import sys
import asyncio
import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings

from . import profile, chat
from .commands import CommandHandler
from .keys.loader import load_api_key, validate_api_key
from .streaming import display_streaming_response
from .chat_manager import prompt_chat_selection, generate_chat_filename


# AI provider imports
from .ai.openai_provider import OpenAIProvider
from .ai.claude_provider import ClaudeProvider
from .ai.gemini_provider import GeminiProvider
from .ai.grok_provider import GrokProvider
from .ai.perplexity_provider import PerplexityProvider
from .ai.mistral_provider import MistralProvider
from .ai.deepseek_provider import DeepSeekProvider

# Type alias for provider instances
ProviderInstance = (
    OpenAIProvider
    | ClaudeProvider
    | GeminiProvider
    | GrokProvider
    | PerplexityProvider
    | MistralProvider
    | DeepSeekProvider
)

# Provider class registry
PROVIDER_CLASSES: dict[str, type] = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "grok": GrokProvider,
    "perplexity": PerplexityProvider,
    "mistral": MistralProvider,
    "deepseek": DeepSeekProvider,
}


@dataclass
class SessionState:
    """Session state for the REPL loop."""

    current_ai: str
    current_model: str
    profile: dict[str, Any]
    chat: dict[str, Any]
    system_prompt: Optional[str] = None
    system_prompt_key: Optional[str] = None
    retry_mode: bool = False
    _provider_cache: dict[tuple[str, str], ProviderInstance] = field(
        default_factory=dict
    )

    def get_cached_provider(
        self, provider_name: str, api_key: str
    ) -> Optional[ProviderInstance]:
        """Get cached provider instance if available."""
        return self._provider_cache.get((provider_name, api_key))

    def cache_provider(
        self, provider_name: str, api_key: str, instance: ProviderInstance
    ) -> None:
        """Cache a provider instance."""
        self._provider_cache[(provider_name, api_key)] = instance


def setup_logging(log_file: Optional[str] = None) -> None:
    """Set up logging configuration.

    Args:
        log_file: Path to log file, or None to disable logging
    """
    if log_file:
        logging.basicConfig(
            filename=log_file,
            level=logging.ERROR,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        # Disable logging
        logging.disable(logging.CRITICAL)


def get_provider_instance(
    provider_name: str, api_key: str, session: Optional[SessionState] = None
) -> ProviderInstance:
    """Get AI provider instance, using cache if available.

    Args:
        provider_name: Name of provider (openai, claude, etc.)
        api_key: API key for provider
        session: Optional session state for caching

    Returns:
        Provider instance

    Raises:
        ValueError: If provider not supported
    """
    # Check cache first
    if session:
        cached = session.get_cached_provider(provider_name, api_key)
        if cached:
            return cached

    provider_class = PROVIDER_CLASSES.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unsupported provider: {provider_name}")

    # Get timeout from profile (default 30)
    timeout = session.profile.get("timeout", 30) if session else 30

    instance = provider_class(api_key, timeout=timeout)

    # Cache the instance
    if session:
        session.cache_provider(provider_name, api_key, instance)

    return instance


async def send_message_to_ai(
    provider_instance: ProviderInstance,
    messages: list[dict],
    model: str,
    system_prompt: Optional[str] = None,
) -> tuple[str, dict]:
    """Send message to AI and get response.

    Args:
        provider_instance: AI provider instance
        messages: Chat messages
        model: Model name
        system_prompt: Optional system prompt

    Returns:
        Tuple of (response_text, metadata)
    """
    try:
        # Stream response
        response_stream = provider_instance.send_message(
            messages=messages, model=model, system_prompt=system_prompt, stream=True
        )

        # Display and accumulate
        response_text = await display_streaming_response(response_stream, prefix="")

        # Get metadata (token usage, etc.)
        # For now, return empty metadata as streaming doesn't provide it
        metadata = {"model": model}

        return response_text, metadata

    except Exception as e:
        logging.error(f"Error sending message to AI: {e}", exc_info=True)
        raise


def validate_and_get_provider(
    session: SessionState,
) -> tuple[Optional[ProviderInstance], Optional[str]]:
    """Validate API key and get provider instance.

    Args:
        session: Session state

    Returns:
        Tuple of (provider_instance, error_message)
        If successful, error_message is None
        If failed, provider_instance is None
    """
    provider_name = session.current_ai
    key_config = session.profile["api_keys"].get(provider_name)

    if not key_config:
        return None, f"No API key configured for {provider_name}"

    try:
        api_key = load_api_key(provider_name, key_config)
    except Exception as e:
        logging.error(f"API key loading error: {e}", exc_info=True)
        return None, f"Error loading API key: {e}"

    if not validate_api_key(api_key, provider_name):
        return None, f"Invalid API key for {provider_name}"

    try:
        provider_instance = get_provider_instance(provider_name, api_key, session)
    except Exception as e:
        logging.error(f"Provider initialization error: {e}", exc_info=True)
        return None, f"Error initializing provider: {e}"

    return provider_instance, None


async def repl_loop(
    profile_data: dict,
    chat_data: Optional[dict] = None,
    chat_path: Optional[str] = None,
    system_prompt: Optional[str] = None,
    system_prompt_key: Optional[str] = None,
) -> None:
    """Run the REPL loop.

    Args:
        profile_data: Loaded profile
        chat_data: Loaded chat history (optional)
        chat_path: Path to chat history file (optional)
        system_prompt: Optional system prompt text
        system_prompt_key: Optional path/key to system prompt (for metadata)
    """
    # Initialize session state (chat can be None)
    session = SessionState(
        current_ai=profile_data["default_ai"],
        current_model=profile_data["models"][profile_data["default_ai"]],
        profile=profile_data,
        chat=chat_data if chat_data else {},
        system_prompt=system_prompt,
        system_prompt_key=system_prompt_key,
    )

    # Set system_prompt_key in chat metadata if chat is loaded
    if chat_data and system_prompt_key and not chat_data["metadata"].get("system_prompt_key"):
        chat.update_metadata(
            chat_data, system_prompt_key=system_prompt_key
        )

    # Initialize command handler (pass session as dict for compatibility)
    session_dict = {
        "current_ai": session.current_ai,
        "current_model": session.current_model,
        "profile": session.profile,
        "chat": session.chat,
        "chat_path": chat_path,
        "system_prompt": session.system_prompt,
        "retry_mode": session.retry_mode,
    }
    cmd_handler = CommandHandler(session_dict)

    # Set up key bindings for message submission
    kb = KeyBindings()

    @kb.add('c-j')  # Ctrl+J (sent by Ctrl+Enter in many terminals)
    @kb.add('escape', 'enter')  # Alt+Enter (Meta+Enter) - most reliable
    def _(event):
        """Submit message on Ctrl+Enter or Alt+Enter."""
        event.current_buffer.validate_and_handle()

    # Set up prompt_toolkit session with history and key bindings
    history_file = Path.home() / ".poly-chat-history"

    prompt_session = PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=kb,
        multiline=True,
    )

    # Get list of configured AI providers
    configured_ais = []
    for provider, model in profile_data["models"].items():
        if provider in profile_data.get("api_keys", {}):
            configured_ais.append(f"{provider} ({model})")

    # Display welcome message
    print("=" * 70)
    print("PolyChat - Multi-AI CLI Chat Tool")
    print("=" * 70)
    print(f"Current Provider: {session.current_ai}")
    print(f"Current Model:    {session.current_model}")
    print(f"Configured AIs:   {', '.join(configured_ais)}")
    if chat_path:
        print(f"Chat:             {Path(chat_path).name}")
    else:
        print(f"Chat:             None (use /new or /open)")
    print()
    print("Press Alt+Enter (or Ctrl+Enter) to send • Enter for new line")
    print("Type /help for commands • Ctrl+D to exit")
    print("=" * 70)
    print()

    # Main REPL loop
    while True:
        try:
            # Get user input (multiline)
            user_input = await prompt_session.prompt_async(
                '',  # Empty prompt
                multiline=True,
                prompt_continuation=lambda width, line_number, is_soft_wrap: ''
            )

            if not user_input.strip():
                continue

            # Check if it's a command
            if cmd_handler.is_command(user_input):
                try:
                    response = await cmd_handler.execute_command(user_input)

                    # Handle special command signals
                    if response == "__EXIT__":
                        print("\nGoodbye!")
                        break

                    elif response.startswith("__NEW_CHAT__:"):
                        # Create new chat
                        new_path = response.split(":", 1)[1]
                        chat_path = new_path
                        chat_data = chat.load_chat(chat_path)

                        # Set system_prompt_key if configured
                        if system_prompt_key:
                            chat.update_metadata(chat_data, system_prompt_key=system_prompt_key)

                        # Update session
                        session.chat = chat_data
                        session_dict["chat"] = chat_data
                        session_dict["chat_path"] = chat_path

                        print(f"Created new chat: {Path(chat_path).name}")
                        print()

                    elif response.startswith("__OPEN_CHAT__:"):
                        # Open existing chat
                        new_path = response.split(":", 1)[1]

                        # Save current chat if any
                        if chat_path and chat_data:
                            await chat.save_chat(chat_path, chat_data)

                        # Load new chat
                        chat_path = new_path
                        chat_data = chat.load_chat(chat_path)

                        # Update session
                        session.chat = chat_data
                        session_dict["chat"] = chat_data
                        session_dict["chat_path"] = chat_path

                        print(f"Opened chat: {Path(chat_path).name}")
                        print()

                    elif response == "__CLOSE_CHAT__":
                        # Save and close current chat
                        if chat_path and chat_data:
                            await chat.save_chat(chat_path, chat_data)

                        chat_path = None
                        chat_data = None

                        # Update session
                        session.chat = {}
                        session_dict["chat"] = {}
                        session_dict["chat_path"] = None

                        print("Chat closed")
                        print()

                    elif response.startswith("__RENAME_CURRENT__:"):
                        # Update current chat path
                        new_path = response.split(":", 1)[1]
                        chat_path = new_path
                        session_dict["chat_path"] = chat_path

                        print(f"Chat renamed to: {Path(chat_path).name}")
                        print()

                    elif response.startswith("__DELETE_CURRENT__:"):
                        # Close current chat after deletion
                        filename = response.split(":", 1)[1]
                        chat_path = None
                        chat_data = None

                        # Update session
                        session.chat = {}
                        session_dict["chat"] = {}
                        session_dict["chat_path"] = None

                        print(f"Deleted and closed chat: {filename}")
                        print()

                    elif response:
                        print(response)
                        print()

                    # Sync session state back from command handler
                    session.current_ai = session_dict["current_ai"]
                    session.current_model = session_dict["current_model"]
                    session.retry_mode = session_dict.get("retry_mode", False)

                except ValueError as e:
                    print(f"Error: {e}")
                    print()
                continue

            # Check if chat is loaded
            if not chat_path:
                print("\nNo chat is currently open.")
                print("Use /new to create a new chat or /open to open an existing one.")
                print()
                continue

            # Validate provider BEFORE adding user message
            provider_instance, error = validate_and_get_provider(session)
            if error:
                print(f"Error: {error}")
                print()
                continue

            # Handle retry mode - remove last assistant message before adding new user message
            if session.retry_mode and chat_data["messages"]:
                last_msg = chat_data["messages"][-1]
                if last_msg["role"] == "assistant":
                    chat_data["messages"].pop()
                    print("[Retry mode: replacing last response]")
                session.retry_mode = False
                session_dict["retry_mode"] = False

            # NOW add user message (after validation passed)
            chat.add_user_message(chat_data, user_input)

            # Get messages for AI
            messages = chat.get_messages_for_ai(chat_data)

            # Send to AI
            try:
                print(f"\n{session.current_ai.capitalize()}: ", end="", flush=True)
                response_text, metadata = await send_message_to_ai(
                    provider_instance,
                    messages,
                    session.current_model,
                    session.system_prompt,
                )

                # Add assistant response to chat
                actual_model = metadata.get("model", session.current_model)
                chat.add_assistant_message(
                    chat_data, response_text, actual_model
                )

                # Save chat history
                await chat.save_chat(
                    chat_path, chat_data
                )

                # Display token usage if available
                if "usage" in metadata:
                    usage = metadata["usage"]
                    print(f"\n[Tokens: {usage.get('total_tokens', 'N/A')}]")

                print()

            except KeyboardInterrupt:
                print("\n[Message cancelled]")
                # Remove the user message since we didn't get a response
                if (
                    chat_data["messages"]
                    and chat_data["messages"][-1]["role"] == "user"
                ):
                    chat_data["messages"].pop()
                print()
                continue

            except Exception as e:
                print(f"\nError: {e}")
                logging.error(f"AI response error: {e}", exc_info=True)

                # Remove user message and add error instead
                if (
                    chat_data["messages"]
                    and chat_data["messages"][-1]["role"] == "user"
                ):
                    chat_data["messages"].pop()

                # Add error message to chat
                chat.add_error_message(
                    chat_data,
                    str(e),
                    {"provider": session.current_ai, "model": session.current_model},
                )

                # Save chat history with error
                await chat.save_chat(
                    chat_path, chat_data
                )
                print()

        except (EOFError, KeyboardInterrupt):
            # Ctrl-D or Ctrl-C at prompt
            print("\nGoodbye!")
            break


def main() -> None:
    """Main entry point for PolyChat CLI."""
    parser = argparse.ArgumentParser(
        description="PolyChat - Multi-AI CLI Chat Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-p", "--profile", required=True, help="Path to profile file (required)"
    )

    parser.add_argument(
        "-c",
        "--chat",
        help="Path to chat history file (optional, will prompt if not provided)",
    )

    parser.add_argument(
        "-l", "--log", help="Path to log file for error logging (optional)"
    )

    parser.add_argument(
        "command", nargs="?", help="Command to run (e.g., 'init' to create profile)"
    )

    args = parser.parse_args()

    # Handle 'init' command for profile creation
    if args.command == "init":
        try:
            profile.create_profile(args.profile)
            sys.exit(0)
        except Exception as e:
            print(f"Error creating profile: {e}")
            sys.exit(1)

    # Set up logging
    setup_logging(args.log)

    try:
        # Load profile
        profile_data = profile.load_profile(args.profile)

        # Get chat history file path (optional)
        chat_path = None
        chat_data = None

        if args.chat:
            # Map the path and load chat
            chat_path = profile.map_path(args.chat)
            chat_data = chat.load_chat(chat_path)

        # Load system prompt if configured
        system_prompt = None
        system_prompt_key = None
        if isinstance(profile_data.get("system_prompt"), str):
            # It's a file path - store the key for metadata
            system_prompt_key = profile_data["system_prompt"]
            try:
                with open(profile_data["system_prompt"], "r", encoding="utf-8") as f:
                    system_prompt = f.read().strip()
            except Exception as e:
                print(f"Warning: Could not load system prompt: {e}")
        elif isinstance(profile_data.get("system_prompt"), dict):
            # It's inline text
            system_prompt = profile_data["system_prompt"].get("content")

        # Run REPL loop
        asyncio.run(
            repl_loop(
                profile_data,
                chat_data,
                chat_path,
                system_prompt,
                system_prompt_key,
            )
        )

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
