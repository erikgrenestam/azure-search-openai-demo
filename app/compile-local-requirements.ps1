# Script to compile local development requirements
# Run this script to update requirements-dev-local.txt when dependencies change

Set-Location $PSScriptRoot

Write-Host "Compiling local development requirements..."

# Check if uv is installed
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Host "uv is not installed. Please install uv first:"
    Write-Host "pip install uv"
    Write-Host "or follow installation instructions at: https://docs.astral.sh/uv/"
    exit 1
}

Set-Location ./backend

Write-Host "Compiling requirements-dev-local.in to requirements-dev-local.txt..."
uv pip compile requirements-dev-local.in -o requirements-dev-local.txt --python-version 3.9

if ($LASTEXITCODE -eq 0) {
    Write-Host "Requirements compiled successfully!"
    Write-Host ""
    Write-Host "IMPORTANT: You still need to manually add your msgraph-sdk .whl file reference to requirements-dev-local.txt"
    Write-Host "Add a line like: ./msgraph_sdk-x.x.x-py3-none-any.whl"
    Write-Host "And place the actual .whl file in the backend directory"
} else {
    Write-Host "Failed to compile requirements"
    exit $LASTEXITCODE
}
