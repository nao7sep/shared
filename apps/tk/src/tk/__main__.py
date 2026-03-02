"""Entry point for running tk as a module."""

# No try/except here — the repl() function in repl.py is the true error
# boundary for the interactive loop, and main() in cli.py handles startup
# errors (profile loading, init). Catching here too would just add a
# redundant wrapper with no additional context.

from tk.cli import main

if __name__ == "__main__":
    main()
