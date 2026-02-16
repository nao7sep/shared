"""Environment variable API key loading for PolyChat."""

import os


def load_from_env(var_name: str) -> str:
    """Load API key from environment variable.

    Args:
        var_name: Environment variable name

    Returns:
        API key string

    Raises:
        ValueError: If variable not set or empty
    """
    value = os.environ.get(var_name)

    if not value:
        raise ValueError(
            f"Environment variable '{var_name}' not set.\n"
            f"Set it with: export {var_name}=your-api-key"
        )

    return value.strip()
