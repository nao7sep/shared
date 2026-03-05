import sys

from . import __version__
from .cli import run_cli
from .errors import EmojihuntError
from .output_segments import reset_segment_state, start_segment


def main() -> None:
    reset_segment_state()
    start_segment()
    print(f"emojihunt {__version__}")
    try:
        run_cli()
    except KeyboardInterrupt:
        print()
        print("Canceled.")
    except EmojihuntError as e:
        start_segment()
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        start_segment()
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
