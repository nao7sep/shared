from .cli import main

# No error handling here. All catch-all handling lives in cli.main() so that
# both `python -m viber` (this module) and the installed `viber` script entry
# point go through exactly the same code path.
if __name__ == "__main__":
    main()
