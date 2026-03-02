"""revzip executable module.

No app-root try/except here: the console script entry point is cli.main(), not
this file, so error handling lives there. This module is only invoked via
`python -m revzip` and delegates immediately to the same main().
"""

from __future__ import annotations

import sys

from .cli import main


if __name__ == "__main__":
    sys.exit(main())
