# Test script for local development environment setup
# This script tests the environment setup without starting the full application

Set-Location $PSScriptRoot

Write-Host "Testing local development environment setup..." -ForegroundColor Green
Write-Host ""

# Check if uv is installed
Write-Host "1. Checking uv installation..." -ForegroundColor Yellow
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Host "   ❌ uv is not installed" -ForegroundColor Red
    exit 1
} else {
    $uvVersion = uv --version
    Write-Host "   ✅ uv is installed: $uvVersion" -ForegroundColor Green
}

# Check for azd
Write-Host "2. Checking azd installation..." -ForegroundColor Yellow
$azdCmd = Get-Command azd -ErrorAction SilentlyContinue
if (-not $azdCmd) {
    Write-Host "   ❌ azd is not installed" -ForegroundColor Red
} else {
    Write-Host "   ✅ azd is available" -ForegroundColor Green
}

# Check for msgraph-sdk .whl file
Write-Host "3. Checking for msgraph-sdk .whl file..." -ForegroundColor Yellow
$wheelFiles = Get-ChildItem -Path "./backend" -Filter "msgraph_sdk*.whl" -ErrorAction SilentlyContinue
if ($wheelFiles.Count -eq 0) {
    Write-Host "   ⚠️  No msgraph-sdk .whl file found in ./backend directory" -ForegroundColor Yellow
    Write-Host "      This is expected if you haven't added your custom .whl file yet" -ForegroundColor Gray
    Write-Host "      The script will fall back to PyPI version during installation" -ForegroundColor Gray
} else {
    $wheelFile = $wheelFiles[0].Name
    Write-Host "   ✅ Found msgraph-sdk wheel file: $wheelFile" -ForegroundColor Green
}

# Check if requirements files exist
Write-Host "4. Checking requirements files..." -ForegroundColor Yellow
$reqFiles = @(
    "./backend/requirements-dev-local.in",
    "./backend/requirements-dev-local.txt"
)

foreach ($file in $reqFiles) {
    if (Test-Path $file) {
        Write-Host "   ✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Missing: $file" -ForegroundColor Red
    }
}

# Test virtual environment creation (without installing packages)
Write-Host "5. Testing virtual environment creation..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "   ✅ .venv already exists" -ForegroundColor Green
} else {
    Write-Host "   Creating test virtual environment..." -ForegroundColor Gray
    uv venv .venv-test
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Virtual environment creation successful" -ForegroundColor Green
        Remove-Item -Recurse -Force ".venv-test" -ErrorAction SilentlyContinue
    } else {
        Write-Host "   ❌ Failed to create virtual environment" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Test complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Place your msgraph-sdk .whl file in ./backend/ directory" -ForegroundColor White
Write-Host "2. Edit ./backend/requirements-dev-local.txt to uncomment and update the .whl file path" -ForegroundColor White
Write-Host "3. Run .\start-local-dev.ps1 to start the local development environment" -ForegroundColor White
