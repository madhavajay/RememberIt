#!/bin/bash
set -e

export UV_VENV_CLEAR=1
uv venv
echo "Installing jupyter dependencies..."
uv pip install jupyter ipykernel
uv pip install -e ./

echo "Starting Jupyter Lab..."
uv run jupyter lab
