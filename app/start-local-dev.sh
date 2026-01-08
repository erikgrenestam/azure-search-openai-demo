#!/bin/bash
# Local development start script using uv and .whl file for msgraph-sdk

set -e

cd "$(dirname "$0")"

echo ""
echo "Loading azd .env file from current environment"
echo ""

# Load environment variables from azd
while IFS= read -r line; do
    if [[ $line == *"="* ]]; then
        export "$line"
    fi
done < <(azd env get-values)

if [ $? -ne 0 ]; then
    echo "Failed to load environment variables from azd environment"
    exit $?
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install uv first:"
    echo "pip install uv"
    echo "or follow installation instructions at: https://docs.astral.sh/uv/"
    exit 1
fi

echo 'Creating python virtual environment ".venv" using uv'
uv venv .venv
if [ $? -ne 0 ]; then
    echo "Failed to create virtual environment with uv"
    exit $?
fi

echo ""
echo "Checking for msgraph-sdk .whl file"
echo ""

wheel_files=(./backend/msgraph_sdk*.whl)
if [ ! -e "${wheel_files[0]}" ]; then
    echo "WARNING: No msgraph-sdk .whl file found in ./backend directory"
    echo "Please place your msgraph-sdk .whl file in the ./backend directory"
    echo "Expected filename pattern: msgraph_sdk*.whl"
    echo ""
    echo "Continuing with PyPI version for now..."
    use_wheel_file=false
else
    wheel_file=$(basename "${wheel_files[0]}")
    echo "Found msgraph-sdk wheel file: $wheel_file"
    use_wheel_file=true
fi

echo ""
echo "Restoring backend python packages using uv"
echo ""

directory=$(pwd)
venv_python_path="$directory/.venv/bin/python"

cd ./backend

if [ "$use_wheel_file" = true ]; then
    # Install dependencies from requirements-dev-local.in (which already excludes msgraph-sdk)
    echo "Installing dependencies from requirements-dev-local.in..."
    uv pip install -r requirements-dev-local.in
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies"
        exit $?
    fi
    
    # Install the local .whl file
    echo "Installing msgraph-sdk from .whl file: $wheel_file"
    uv pip install "./$wheel_file"
    if [ $? -ne 0 ]; then
        echo "Failed to install msgraph-sdk from .whl file"
        exit $?
    fi
else
    # Fallback: install all dependencies including msgraph-sdk from PyPI
    echo "Installing all dependencies from PyPI (including msgraph-sdk)..."
    # Create a temporary requirements file that includes msgraph-sdk
    cat > temp-requirements.txt << 'EOF'
azure-identity
quart
quart-cors
openai>=1.3.7
tiktoken
tenacity
azure-ai-documentintelligence==1.0.0b4
azure-cognitiveservices-speech
azure-cosmos
azure-search-documents==11.6.0b12
azure-storage-blob
azure-storage-file-datalake
uvicorn
aiohttp
azure-monitor-opentelemetry
opentelemetry-instrumentation-asgi
opentelemetry-instrumentation-httpx
opentelemetry-instrumentation-aiohttp-client
opentelemetry-instrumentation-openai
msal
cryptography
PyJWT
Pillow
types-Pillow
pypdf
PyMuPDF
beautifulsoup4
types-beautifulsoup4
msgraph-sdk
python-dotenv
prompty
rich
typing-extensions
ruff
black
pytest
pytest-asyncio
pytest-snapshot
coverage
playwright
pytest-cov
pytest-playwright
pytest-snapshot
pre-commit
pip-tools
mypy==1.14.1
diff_cover
axe-playwright-python
EOF
    uv pip install -r temp-requirements.txt
    rm -f temp-requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to restore backend python packages"
        exit $?
    fi
fi

echo ""
echo "Restoring frontend npm packages"
echo ""
cd ../frontend
npm install
if [ $? -ne 0 ]; then
    echo "Failed to restore frontend npm packages"
    exit $?
fi

echo ""
echo "Building frontend"
echo ""
npm run build
if [ $? -ne 0 ]; then
    echo "Failed to build frontend"
    exit $?
fi

echo ""
echo "Starting backend using local venv"
echo ""
cd ../backend

port=50505
hostname="localhost"

# Activate the local venv and start the backend
source "$directory/.venv/bin/activate"
$venv_python_path -m quart --app main:app run --port $port --host $hostname --reload

if [ $? -ne 0 ]; then
    echo "Failed to start backend"
    exit $?
fi
