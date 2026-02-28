#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "PolyChat models integration test"
echo ""
echo "Syncing dependencies..."
uv sync --group dev
echo ""
echo "Requires .dev-api-keys.json with valid API keys."
echo ""
echo "Options:"
echo "  1. Test every model (34 models, slower)"
echo "  2. Test default models only (7 models, faster)"
echo "  3. Cancel"
echo ""
read "choice?Select [1-3]: "

case $choice in
    1)
        echo "Running models smoke test..."
        uv run pytest tests/test_models_integration.py::test_all_models_smoke_test -v -s -m integration
        ;;
    2)
        echo "Running default models test..."
        uv run pytest tests/test_models_integration.py::test_default_models_work -v -s -m integration
        ;;
    3)
        echo "Cancelled."
        ;;
    *)
        echo "ERROR: Invalid choice."
        exit 1
        ;;
esac
