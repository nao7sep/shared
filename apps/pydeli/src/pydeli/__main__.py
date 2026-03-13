from __future__ import annotations

from .cli import run
from .errors import PydeliError
from .output_segments import reset_segments, start_segment

from . import __version__


def main() -> int:
    reset_segments()

    start_segment()
    print(f"pydeli {__version__}")

    try:
        run()
        start_segment()
        print("Done.")
        return 0
    except KeyboardInterrupt:
        start_segment()
        print("Interrupted.")
        return 130
    except EOFError:
        start_segment()
        print("Interrupted.")
        return 130
    except PydeliError as error:
        start_segment()
        print(f"Error: {error}")
        return 1
    except Exception as error:
        start_segment()
        print(f"Error: Unexpected failure: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
