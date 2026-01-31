# tk

A quick CLI app to manage tasks.

## Installation

```bash
poetry install
```

## Usage

```bash
# Run directly
poetry run tk --profile ~/path/to/profile.json

# Or install and run
poetry install
tk --profile ~/path/to/profile.json
```

## Quick Start

1. Create a new profile:
```
tk> new ~/work/my-profile.json
```

2. Add tasks:
```
tk> add "implement user authentication"
```

3. List tasks:
```
tk> list
```

4. Mark as done:
```
tk> done 1 --note "completed successfully"
```

See WHAT.md and HOW.md for detailed documentation.
