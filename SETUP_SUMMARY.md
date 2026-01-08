# Local Development Environment with uv and Custom msgraph-sdk

## Summary

I've set - **Isolated Environment**: Uses `.venv` and is compatible with the standard azd setupp a complete local development environment that uses `uv` as the package manager and supports using a custom `.whl` file for `msgraph-sdk` instead of the PyPI version. Here's what has been created:

## New Files Created

### Scripts
- **`app/start-local-dev.ps1`** - PowerShell script for Windows to start local development
- **`app/start-local-dev.sh`** - Bash script for Linux/macOS to start local development  
- **`app/compile-local-requirements.ps1`** - PowerShell script to compile requirements
- **`app/compile-local-requirements.sh`** - Bash script to compile requirements
- **`app/test-local-setup.ps1`** - Test script to validate environment setup

### Requirements Files
- **`app/backend/requirements-dev-local.in`** - Input requirements file (excludes msgraph-sdk)
- **`app/backend/requirements-dev-local.txt`** - Compiled requirements file with placeholder for .whl

### Documentation
- **`app/LOCAL_DEV_README.md`** - Comprehensive setup and usage documentation

### VS Code Integration
- Updated **`.vscode/tasks.json`** with new tasks:
  - "Start App (Local Dev with uv)"
  - "Local Development (uv)" 
  - "Backend: quart run (Local uv)"
  - "Compile Local Requirements"

## Key Features

### 1. uv Package Manager
- Uses `uv` for faster, more reliable package management
- Creates isolated `.venv-local` virtual environment (separate from standard `.venv`)
- Supports both Windows PowerShell and Linux/macOS bash environments

### 2. Custom msgraph-sdk Support
- Automatically detects `.whl` files in `app/backend/` directory
- Falls back to PyPI version if no `.whl` file is found
- Easy to switch between custom and standard versions

### 3. Smart Installation Process
1. Checks for required tools (uv, azd)
2. Loads environment variables from azd
3. Creates virtual environment with uv
4. Installs dependencies (excluding msgraph-sdk if .whl file present)
5. Installs custom msgraph-sdk from .whl file
6. Builds frontend and starts backend

### 4. Cross-Platform Compatibility
- PowerShell scripts for Windows
- Bash scripts for Linux/macOS
- Unified VS Code tasks work on all platforms

## How to Use

### Quick Start
1. **Install uv**: `pip install uv`
2. **Place your .whl file**: Copy `msgraph_sdk-*.whl` to `app/backend/` directory
3. **Test setup**: Run `.\app\test-local-setup.ps1`
4. **Start development**: Run `.\app\start-local-dev.ps1`

### VS Code Integration
- Use Command Palette (Ctrl+Shift+P) → "Tasks: Run Task"
- Select "Start App (Local Dev with uv)" for complete setup
- Select "Local Development (uv)" for development servers only

### Manual Package Management
- **Compile requirements**: `.\app\compile-local-requirements.ps1`
- **Add new dependencies**: Edit `app/backend/requirements-dev-local.in` then recompile

## Directory Structure
```
app/
├── start-local-dev.ps1           # Main start script (Windows)
├── start-local-dev.sh            # Main start script (Linux/macOS)
├── compile-local-requirements.ps1 # Compile requirements (Windows)
├── compile-local-requirements.sh  # Compile requirements (Linux/macOS)
├── test-local-setup.ps1          # Test environment setup
├── LOCAL_DEV_README.md           # Detailed documentation
├── backend/
│   ├── requirements-dev-local.in  # Input requirements (no msgraph-sdk)
│   ├── requirements-dev-local.txt # Compiled requirements + .whl placeholder
│   └── [your-msgraph-sdk.whl]    # Place your .whl file here
└── .venv/                        # Virtual environment (created automatically)
```

## Important Notes

1. **Virtual Environment**: Uses `.venv` which is compatible with the standard azd setup
2. **Fallback Behavior**: If no .whl file is found, installs msgraph-sdk from PyPI
3. **Environment Variables**: Automatically loads from azd environment
4. **VS Code Tasks**: Integrated with VS Code task system for easy access

## Troubleshooting

- **Run test script first**: `.\app\test-local-setup.ps1` validates your environment
- **Check uv installation**: Ensure `uv --version` works
- **Verify .whl file**: Must be in `app/backend/` with pattern `msgraph_sdk*.whl`
- **Permission issues**: On Linux/macOS, ensure scripts are executable (`chmod +x *.sh`)

The local development environment is now ready! The existing standard setup (`start.ps1`) remains unchanged, so you can use either approach as needed.
