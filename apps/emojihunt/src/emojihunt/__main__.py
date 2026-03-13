"""emojihunt executable module.

Delegates to cli.main() so that both `python -m emojihunt` and the installed
`emojihunt` script entry point go through exactly the same code path.
"""

from .cli import main

if __name__ == "__main__":
    main()
