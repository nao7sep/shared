#!/bin/zsh
cd "$(dirname "$0")/.."
echo "PolyChat Models Integration Test"
echo "================================="
echo ""
echo "This will test models in the registry with real API calls."
echo "Requires .TEST_API_KEYS.json with valid API keys."
echo ""
echo "Options:"
echo "  1. Test every model (34 models, slower)"
echo "  2. Test default models only (7 models, faster)"
echo "  3. Cancel"
echo ""
read -p "Select [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "Running models smoke test..."
        echo ""
        uv run pytest tests/test_models_integration.py::test_all_models_smoke_test -v -s -m integration
        ;;
    2)
        echo ""
        echo "Running default models test..."
        echo ""
        uv run pytest tests/test_models_integration.py::test_default_models_work -v -s -m integration
        ;;
    3)
        echo "Cancelled."
        ;;
    *)
        echo "Invalid choice."
        ;;
esac
