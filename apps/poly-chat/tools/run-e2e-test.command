#!/bin/bash
# Quick launcher for end-to-end test

cd "$(dirname "$0")/.."

echo "Running PolyChat End-to-End Test..."
echo ""

poetry run pytest tests/test_ai/test_end_to_end.py -v -s -m e2e

echo ""
read -p "Press Enter to close..."
