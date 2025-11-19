#!/bin/bash
set -e

echo "Running ruff check..."
uv run ruff check --fix src tests

echo "Running ruff format check..."
uv run ruff format src tests

echo "Running mypy..."
uv run mypy src/rememberit

echo "Running vulture (dead code detection)..."
uv run vulture src tests .vulture_whitelist.py --min-confidence 80

echo "✓ All linting checks passed!"
