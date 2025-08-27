# Check if uv is installed
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Host "uv is not installed. Please install uv first:"
    Write-Host "pip install uv"
    Write-Host "or follow installation instructions at: https://docs.astral.sh/uv/"
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Host 'Creating python virtual environment ".venv" using uv'
    uv venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment with uv"
        exit $LASTEXITCODE
    }
} else {
    Write-Host 'Virtual environment ".venv" already exists, skipping creation'
}

$directory = Get-Location
$venvPythonPath = "$directory/.venv/Scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "$directory/.venv/bin/python"
}

Write-Host 'Installing dependencies from "requirements-dev-local.txt" into virtual environment using uv'
uv pip install -r app/backend/requirements-dev-local.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies"
    exit $LASTEXITCODE
}
