"""Entry point for running PolyChat as a module.

This allows running: python -m polychat
"""

from .cli import main

if __name__ == "__main__":
    # No try/except here: main() is the CLI boundary and already catches all
    # exceptions, logs them, and exits with the appropriate code.
    main()
