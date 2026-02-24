"""Runtime command handlers for provider/model/helper and timeout selection."""

from typing import TYPE_CHECKING

from ..ai.catalog import (
    get_all_providers,
    get_models_for_provider,
    get_provider_for_model,
    resolve_model_candidates,
    resolve_provider_shortcut,
)
from ..constants import DISPLAY_UNKNOWN
from ..timeouts import resolve_profile_timeout

if TYPE_CHECKING:
    from .contracts import CommandDependencies as _CommandDependencies
else:
    class _CommandDependencies:
        pass


class RuntimeModelCommandsMixin(_CommandDependencies):
    async def _choose_model_from_candidates(
        self,
        query: str,
        candidates: list[str],
    ) -> tuple[str | None, str | None]:
        """Prompt user to select one model when multiple candidates match."""
        prompt_lines = [f"Multiple models match '{query}':"]
        for index, model_name in enumerate(candidates, start=1):
            provider_name = get_provider_for_model(model_name) or DISPLAY_UNKNOWN
            prompt_lines.append(f"  {index}. {model_name} ({provider_name})")
        prompt_lines.append("Select one by number (press Enter to cancel).")

        answer = (await self._prompt_text("\n".join(prompt_lines) + "\nSelection: ")).strip()
        if not answer:
            return None, "Model selection cancelled."
        if not answer.isdigit():
            return None, "Invalid selection. Enter a number from the list."

        selected_index = int(answer)
        if selected_index < 1 or selected_index > len(candidates):
            return None, f"Invalid selection. Choose a number between 1 and {len(candidates)}."

        return candidates[selected_index - 1], None

    async def _resolve_model_selection(self, query: str) -> tuple[str | None, str]:
        """Resolve a model query to one selected model."""
        candidates = resolve_model_candidates(query)
        if not candidates:
            return None, f"No model matches '{query}'."
        if len(candidates) == 1:
            return candidates[0], ""

        selected_model, selection_error = await self._choose_model_from_candidates(
            query,
            candidates,
        )
        if selection_error:
            return None, selection_error
        if selected_model is None:
            return None, "Model selection cancelled."
        return selected_model, ""

    async def set_model(self, args: str) -> str:
        """Set the current model.

        Args:
            args: Model query, "default" to revert to profile default, or empty to show list

        Returns:
            Confirmation message or model list
        """
        if not args:
            provider = self.manager.current_ai
            available_models = get_models_for_provider(provider)
            return f"Available models for {provider}:\n" + "\n".join(
                f"  - {m}" for m in available_models
            )

        if args == "default":
            profile_data = self.manager.profile
            default_ai = profile_data["default_ai"]
            default_model = profile_data["models"][default_ai]

            self.manager.current_ai = default_ai
            self.manager.current_model = default_model

            notices = self._reconcile_provider_modes(default_ai)
            if notices:
                return (
                    f"Reverted to profile default: {default_ai} ({default_model})\n"
                    + "\n".join(notices)
                )
            return f"Reverted to profile default: {default_ai} ({default_model})"

        query = args.strip()
        selected_model, resolution_error = await self._resolve_model_selection(query)
        if resolution_error:
            return resolution_error
        if selected_model is None:
            return "Model selection cancelled."
        assert selected_model is not None

        model_provider = get_provider_for_model(selected_model)
        if model_provider is None:
            return f"No provider found for model '{selected_model}'."

        self.manager.current_ai = model_provider
        self.manager.current_model = selected_model

        base_message = f"Switched to {model_provider} ({selected_model})"
        if selected_model != query:
            base_message += f" [matched from '{query}']"
        notices = self._reconcile_provider_modes(model_provider)
        if notices:
            return base_message + "\n" + "\n".join(notices)
        return base_message

    async def set_helper(self, args: str) -> str:
        """Set or show the helper AI model.

        Args:
            args: Model query/provider shortcut, 'default' to revert, or empty to show current

        Returns:
            Confirmation message or current helper
        """
        if not args:
            helper_ai = self.manager.helper_ai
            helper_model = self.manager.helper_model
            return f"Current helper AI: {helper_ai} ({helper_model})"

        if args == "default":
            profile_data = self.manager.profile
            helper_ai_name = profile_data.get("default_helper_ai", profile_data["default_ai"])
            helper_model_name = profile_data["models"][helper_ai_name]

            self.manager.helper_ai = helper_ai_name
            self.manager.helper_model = helper_model_name

            return f"Helper AI restored to profile default: {helper_ai_name} ({helper_model_name})"

        query = args.strip()
        lowered = query.lower()

        provider_shortcut = resolve_provider_shortcut(lowered)
        if provider_shortcut is not None:
            provider_model = self.manager.profile["models"].get(provider_shortcut)
            if not provider_model:
                return f"No model configured for {provider_shortcut} in profile"
            self.manager.helper_ai = provider_shortcut
            self.manager.helper_model = provider_model
            return f"Helper AI set to {provider_shortcut} ({provider_model})"

        if lowered in get_all_providers():
            provider_model = self.manager.profile["models"].get(lowered)
            if not provider_model:
                return f"No model configured for {lowered} in profile"
            self.manager.helper_ai = lowered
            self.manager.helper_model = provider_model
            return f"Helper AI set to {lowered} ({provider_model})"

        selected_model, resolution_error = await self._resolve_model_selection(query)
        if resolution_error:
            return resolution_error
        if selected_model is None:
            return "Helper model selection cancelled."

        provider = get_provider_for_model(selected_model)
        if provider is None:
            return f"No provider found for model '{selected_model}'."

        self.manager.helper_ai = provider
        self.manager.helper_model = selected_model

        message = f"Helper AI set to {provider} ({selected_model})"
        if selected_model != query:
            message += f" [matched from '{query}']"
        return message

    async def set_timeout(self, args: str) -> str:
        """Set or show the timeout setting.

        Args:
            args: Timeout in seconds, "default" to revert to profile default, or empty to show current

        Returns:
            Confirmation message or current timeout
        """
        if not args:
            timeout = resolve_profile_timeout(self.manager.profile)
            return f"Current timeout: {self.manager.format_timeout(timeout)}"

        if args == "default":
            default_timeout = self.manager.reset_timeout_to_default()
            return f"Reverted to profile default: {self.manager.format_timeout(default_timeout)}"

        try:
            timeout = self.manager.set_timeout(float(args))
            return f"Timeout set to {self.manager.format_timeout(timeout)}"

        except ValueError:
            raise ValueError(
                "Invalid timeout value. Use a number (e.g., /timeout 60) or 0 for no timeout."
            )
