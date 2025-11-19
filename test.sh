#!/bin/bash
set -e

echo "Running tests with pytest..."
uv run pytest tests/ -v "$@"
