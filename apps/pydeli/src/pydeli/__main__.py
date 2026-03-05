__version__ = "0.1.0.dev1"

import sys

from .cli import main as _main
from .errors import PydeliError


def main() -> None:
    try:
        _main()
    except SystemExit:
        raise
    except PydeliError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
