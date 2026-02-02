"""CLI entry point and REPL loop for PolyChat."""

import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from . import profile, conversation
from .commands import CommandHandler
from .keys.loader import load_api_key, validate_api_key
from .streaming import display_streaming_response


# AI provider imports
from .ai.openai_provider import OpenAIProvider
from .ai.claude_provider import ClaudeProvider
from .ai.gemini_provider import GeminiProvider
from .ai.grok_provider import GrokProvider
from .ai.perplexity_provider import PerplexityProvider
from .ai.mistral_provider import MistralProvider
from .ai.deepseek_provider import DeepSeekProvider


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


def get_provider_instance(provider_name: str, api_key: str):
    """Get AI provider instance.

    Args:
        provider_name: Name of provider (openai, claude, etc.)
        api_key: API key for provider

    Returns:
        Provider instance

    Raises:
        ValueError: If provider not supported
    """
    providers = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider,
        "grok": GrokProvider,
        "perplexity": PerplexityProvider,
        "mistral": MistralProvider,
        "deepseek": DeepSeekProvider,
    }

    provider_class = providers.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unsupported provider: {provider_name}")

    return provider_class(api_key)


async def send_message_to_ai(
    provider_instance,
    messages: list[dict],
    model: str,
    system_prompt: Optional[str] = None,
) -> tuple[str, dict]:
    """Send message to AI and get response.

    Args:
        provider_instance: AI provider instance
        messages: Conversation messages
        model: Model name
        system_prompt: Optional system prompt

    Returns:
        Tuple of (response_text, metadata)
    """
    try:
        # Stream response
        stream = provider_instance.send_message(
            messages=messages, model=model, system_prompt=system_prompt, stream=True
        )

        # Display and accumulate
        response_text = await display_streaming_response(stream, prefix="")

        # Get metadata (token usage, etc.)
        # For now, return empty metadata as streaming doesn't provide it
        metadata = {"model": model}

        return response_text, metadata

    except Exception as e:
        logging.error(f"Error sending message to AI: {e}", exc_info=True)
        raise


async def repl_loop(
    profile_data: dict,
    conversation_data: dict,
    conversation_path: str,
    system_prompt: Optional[str] = None,
) -> None:
    """Run the REPL loop.

    Args:
        profile_data: Loaded profile
        conversation_data: Loaded conversation
        conversation_path: Path to conversation file
        system_prompt: Optional system prompt text
    """
    # Initialize session state
    session = {
        "current_ai": profile_data["default_ai"],
        "current_model": profile_data["models"][profile_data["default_ai"]],
        "profile": profile_data,
        "conversation": conversation_data,
        "system_prompt": system_prompt,
    }

    # Initialize command handler
    cmd_handler = CommandHandler(session)

    # Set up prompt_toolkit session with history
    history_file = Path.home() / ".poly-chat-history"
    prompt_session = PromptSession(history=FileHistory(str(history_file)))

    # Display welcome message
    print("=" * 60)
    print("PolyChat - Multi-AI CLI Chat Tool")
    print("=" * 60)
    print(f"Provider: {session['current_ai']}")
    print(f"Model: {session['current_model']}")
    print("Type /help for commands, Ctrl-D or /exit to quit")
    print("=" * 60)
    print()

    # Main REPL loop
    while True:
        try:
            # Get user input (multiline)
            user_input = await prompt_session.prompt_async("You: ", multiline=True)

            if not user_input.strip():
                continue

            # Check if it's a command
            if cmd_handler.is_command(user_input):
                try:
                    response = await cmd_handler.execute_command(user_input)
                    if response == "__EXIT__":
                        print("\nGoodbye!")
                        break
                    if response:
                        print(response)
                        print()
                except ValueError as e:
                    print(f"Error: {e}")
                    print()
                continue

            # Add user message to conversation
            conversation.add_user_message(conversation_data, user_input)

            # Load API key for current provider
            try:
                provider_name = session["current_ai"]
                key_config = profile_data["api_keys"].get(provider_name)

                if not key_config:
                    print(f"Error: No API key configured for {provider_name}")
                    print()
                    continue

                api_key = load_api_key(provider_name, key_config)

                if not validate_api_key(api_key, provider_name):
                    print(f"Error: Invalid API key for {provider_name}")
                    print()
                    continue

            except Exception as e:
                print(f"Error loading API key: {e}")
                logging.error(f"API key loading error: {e}", exc_info=True)
                print()
                continue

            # Get provider instance
            try:
                provider_instance = get_provider_instance(provider_name, api_key)
            except Exception as e:
                print(f"Error initializing provider: {e}")
                logging.error(f"Provider initialization error: {e}", exc_info=True)
                print()
                continue

            # Get messages for AI
            messages = conversation.get_messages_for_ai(conversation_data)

            # Send to AI
            try:
                print(f"\n{session['current_ai'].capitalize()}: ", end="", flush=True)
                response_text, metadata = await send_message_to_ai(
                    provider_instance, messages, session["current_model"], system_prompt
                )

                # Add assistant response to conversation
                actual_model = metadata.get("model", session["current_model"])
                conversation.add_assistant_message(
                    conversation_data, response_text, actual_model
                )

                # Save conversation
                await conversation.save_conversation(
                    conversation_path, conversation_data
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
                    conversation_data["messages"]
                    and conversation_data["messages"][-1]["role"] == "user"
                ):
                    conversation_data["messages"].pop()
                print()
                continue

            except Exception as e:
                print(f"\nError: {e}")
                logging.error(f"AI response error: {e}", exc_info=True)

                # Add error message to conversation
                conversation.add_error_message(
                    conversation_data,
                    str(e),
                    {"provider": provider_name, "model": session["current_model"]},
                )

                # Save conversation with error
                await conversation.save_conversation(
                    conversation_path, conversation_data
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
        help="Path to conversation file (optional, will prompt if not provided)",
    )

    parser.add_argument(
        "-l", "--log", help="Path to log file for error logging (optional)"
    )

    parser.add_argument(
        "command", nargs="?", help="Command to run (e.g., 'new' to create profile)"
    )

    args = parser.parse_args()

    # Handle 'new' command for profile creation
    if args.command == "new":
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
        print("Loading profile...")
        profile_data = profile.load_profile(args.profile)

        # Get conversation file path
        if args.chat:
            # Map the path
            conversation_path = profile.map_path(
                args.chat, str(Path(args.profile).parent)
            )
        else:
            # Prompt for conversation file
            print("\nConversation file:")
            print("  1. Open existing")
            print("  2. Create new")
            choice = input("Select option (1/2) [2]: ").strip() or "2"

            if choice == "1":
                conv_name = input("Enter conversation file name or path: ").strip()
                if not conv_name:
                    print("Error: Conversation file name required")
                    sys.exit(1)
                conversation_path = profile.map_path(
                    conv_name, profile_data["conversations_dir"]
                )
            else:
                # Generate new filename
                import uuid

                conv_name = f"poly-chat_{uuid.uuid4()}.json"
                conversation_path = str(
                    Path(profile_data["conversations_dir"]) / conv_name
                )
                print(f"Creating new conversation: {conv_name}")

        # Load conversation
        print("Loading conversation...")
        conversation_data = conversation.load_conversation(conversation_path)

        # Load system prompt if configured
        system_prompt = None
        if isinstance(profile_data.get("system_prompt"), str):
            # It's a file path
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
            repl_loop(profile_data, conversation_data, conversation_path, system_prompt)
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
