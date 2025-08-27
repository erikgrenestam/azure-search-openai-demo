#!/bin/bash
# Script to compile local development requirements
# Run this script to update requirements-dev-local.txt when dependencies change

set -e

cd "$(dirname "$0")"

echo "Compiling local development requirements..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install uv first:"
    echo "pip install uv"
    echo "or follow installation instructions at: https://docs.astral.sh/uv/"
    exit 1
fi

cd ./backend

echo "Compiling requirements-dev-local.in to requirements-dev-local.txt..."
uv pip compile requirements-dev-local.in -o requirements-dev-local.txt --python-version 3.9

if [ $? -eq 0 ]; then
    echo "Requirements compiled successfully!"
    echo ""
    echo "IMPORTANT: You still need to manually add your msgraph-sdk .whl file reference to requirements-dev-local.txt"
    echo "Add a line like: ./msgraph_sdk-x.x.x-py3-none-any.whl"
    echo "And place the actual .whl file in the backend directory"
else
    echo "Failed to compile requirements"
    exit $?
fi
