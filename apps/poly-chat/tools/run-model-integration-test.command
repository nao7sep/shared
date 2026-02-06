#!/bin/bash
# Quick launcher for model integration test

cd "$(dirname "$0")/.."

echo "PolyChat Model Integration Test"
echo "================================"
echo ""
echo "This will test ALL models in the registry with real API calls."
echo "Requires .TEST_API_KEYS.json with valid API keys."
echo ""
echo "Options:"
echo "  1. Test all models (37 models, slower)"
echo "  2. Test default models only (7 models, faster)"
echo "  3. Cancel"
echo ""
read -p "Select [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "Running ALL models smoke test..."
        echo ""
        poetry run pytest tests/test_all_models_integration.py::test_all_models_smoke_test -v -s -m integration
        ;;
    2)
        echo ""
        echo "Running default models test..."
        echo ""
        poetry run pytest tests/test_all_models_integration.py::test_default_models_work -v -s -m integration
        ;;
    3)
        echo "Cancelled."
        ;;
    *)
        echo "Invalid choice."
        ;;
esac

echo ""
read -p "Press Enter to close..."
