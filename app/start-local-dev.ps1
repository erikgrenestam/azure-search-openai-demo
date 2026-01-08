# Local development start script using uv and .whl file for msgraph-sdk
# set the parent of the script as the current location.
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "Loading azd .env file from current environment"
Write-Host ""

foreach ($line in (& azd env get-values)) {
    if ($line -match "([^=]+)=(.*)") {
        $key = $matches[1]
        $value = $matches[2] -replace '^"|"$'
        Set-Item -Path "env:\$key" -Value $value
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to load environment variables from azd environment"
    exit $LASTEXITCODE
}

# Check if uv is installed
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Host "uv is not installed. Please install uv first:"
    Write-Host "pip install uv"
    Write-Host "or follow installation instructions at: https://docs.astral.sh/uv/"
    exit 1
}

Write-Host 'Creating python virtual environment ".venv" using uv'
uv venv .venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create virtual environment with uv"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Checking for msgraph-sdk .whl file"
Write-Host ""

$wheelFiles = Get-ChildItem -Path "./backend" -Filter "msgraph_sdk*.whl" -ErrorAction SilentlyContinue
if ($wheelFiles.Count -eq 0) {
    Write-Host "WARNING: No msgraph-sdk .whl file found in ./backend directory"
    Write-Host "Please place your msgraph-sdk .whl file in the ./backend directory"
    Write-Host "Expected filename pattern: msgraph_sdk*.whl"
    Write-Host ""
    Write-Host "Continuing with PyPI version for now..."
    $useWheelFile = $false
} else {
    $wheelFile = $wheelFiles[0].Name
    Write-Host "Found msgraph-sdk wheel file: $wheelFile"
    $useWheelFile = $true
}

Write-Host ""
Write-Host "Restoring backend python packages using uv"
Write-Host ""

$directory = Get-Location
$venvPythonPath = "$directory/.venv/Scripts/python.exe"
if (Test-Path -Path "/usr") {
    # fallback to Linux venv path
    $venvPythonPath = "$directory/.venv/bin/python"
}

Set-Location ./backend

if ($useWheelFile) {
    # Install dependencies from requirements-dev-local.in (which already excludes msgraph-sdk)
    Write-Host "Installing dependencies from requirements-dev-local.in..."
    uv pip install -r requirements-dev-local.in
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install dependencies"
        exit $LASTEXITCODE
    }
    
    # Install the local .whl file
    Write-Host "Installing msgraph-sdk from .whl file: $wheelFile"
    uv pip install "./$wheelFile"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install msgraph-sdk from .whl file"
        exit $LASTEXITCODE
    }
} else {
    # Fallback: install all dependencies including msgraph-sdk from PyPI
    Write-Host "Installing all dependencies from PyPI (including msgraph-sdk)..."
    # Create a temporary requirements file that includes msgraph-sdk
    $tempReqs = @"
azure-identity
quart
quart-cors
openai>=1.3.7
docling==2.34.0
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
"@
    $tempReqs | Out-File -FilePath "temp-requirements.txt" -Encoding utf8
    uv pip install -r temp-requirements.txt
    Remove-Item "temp-requirements.txt" -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to restore backend python packages"
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "Restoring frontend npm packages"
Write-Host ""
Set-Location ../frontend
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to restore frontend npm packages"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Building frontend"
Write-Host ""
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build frontend"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Starting backend using local venv"
Write-Host ""
Set-Location ../backend

$port = 50505
$hostname = "localhost"

# Set environment variables for Quart
$env:QUART_APP = "main:app"
$env:QUART_ENV = "development"
$env:QUART_DEBUG = "0"
$env:LOADING_MODE_FOR_AZD_ENV_VARS = "override"

# Start the backend using the virtual environment Python
Write-Host "Running: $venvPythonPath -m quart run --reload --port $port --host $hostname"
& $venvPythonPath -m quart run --reload --port $port --host $hostname

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start backend"
    exit $LASTEXITCODE
}
