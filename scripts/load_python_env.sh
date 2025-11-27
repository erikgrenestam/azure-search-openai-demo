#!/bin/sh
set -eu

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Please install uv first:"
    echo "  pip install uv"
    echo "or follow installation instructions at: https://docs.astral.sh/uv/"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo 'Creating python virtual environment ".venv" using uv'
    uv venv .venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment with uv"
        exit 1
    fi
else
    echo 'Virtual environment ".venv" already exists, skipping creation'
fi

# Determine the venv python path (platform-aware)
venv_python=".venv/bin/python"
if [ -f ".venv/Scripts/python.exe" ]; then
    venv_python=".venv/Scripts/python.exe"
fi

echo 'Installing dependencies from "app/backend/requirements-dev-local.txt" into virtual environment using uv'
uv pip install -r app/backend/requirements-dev-local.txt
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies"
    exit 1
fi
