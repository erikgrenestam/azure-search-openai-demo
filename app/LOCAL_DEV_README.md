# Local Development Setup with uv and msgraph-sdk .whl

This directory contains scripts and configuration for local development using `uv` as the package manager and a local `.whl` file for the `msgraph-sdk` package.

## Prerequisites

1. **Install uv**: 
   ```bash
   pip install uv
   ```
   Or follow the installation instructions at: https://docs.astral.sh/uv/

2. **Obtain msgraph-sdk .whl file**: 
   - Place your custom `msgraph-sdk` .whl file in the `app/backend/` directory
   - The filename should match the pattern: `msgraph_sdk*.whl`

## Setup Instructions

### Option 1: Automatic Setup (Recommended)

Run the local development start script:

**Windows (PowerShell):**
```powershell
.\app\start-local-dev.ps1
```

**Linux/macOS:**
```bash
./app/start-local-dev.sh
```

This script will:
1. Load environment variables from azd
2. Create a `.venv` virtual environment using uv
3. Install dependencies, using your local .whl file for msgraph-sdk if available
4. Build the frontend
5. Start the backend server

### Option 2: Manual Setup

1. **Compile requirements** (optional, if you've modified dependencies):
   ```powershell
   # Windows
   .\app\compile-local-requirements.ps1
   
   # Linux/macOS
   ./app/compile-local-requirements.sh
   ```

2. **Create virtual environment**:
   ```bash
   cd app
   uv venv .venv
   ```

3. **Install dependencies**:
   ```bash
   cd backend
   
   # If you have a msgraph-sdk .whl file:
   uv pip install -r requirements-dev-local.in --exclude msgraph-sdk
   uv pip install ./msgraph_sdk-*.whl
   
   # If you don't have a .whl file (fallback to PyPI):
   uv pip install -r requirements-dev-local.in msgraph-sdk
   ```

4. **Build frontend**:
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

5. **Start backend**:
   ```bash
   cd ../backend
   # Activate virtual environment
   source ../.venv/bin/activate  # Linux/macOS
   # OR
   ..\.venv\Scripts\Activate.ps1  # Windows
   
   python -m quart --app main:app run --port 50505 --host localhost --reload
   ```

## VS Code Tasks

The following VS Code tasks are available:

- **Start App (Local Dev with uv)**: Complete setup and start using the local development environment
- **Local Development (uv)**: Start frontend and backend development servers using the local uv environment
- **Backend: quart run (Local uv)**: Start only the backend using the local uv virtual environment
- **Compile Local Requirements**: Compile the requirements-dev-local.in file to requirements-dev-local.txt

## File Structure

- `start-local-dev.ps1/.sh`: Main start script for local development
- `compile-local-requirements.ps1/.sh`: Script to compile requirements files
- `backend/requirements-dev-local.in`: Input requirements file (excludes msgraph-sdk)
- `backend/requirements-dev-local.txt`: Compiled requirements file
- `.venv/`: Local virtual environment directory (created automatically)

## Notes

- The local environment uses `.venv` and is compatible with the standard azd setup
- If no `.whl` file is found, the scripts will fall back to using the PyPI version of msgraph-sdk
- Make sure to place your `.whl` file in the `app/backend/` directory before running the setup scripts
- The compiled requirements file may need manual editing to include the correct path to your `.whl` file

## Troubleshooting

1. **uv not found**: Make sure uv is installed and available in your PATH
2. **No .whl file found**: The script will continue with PyPI version, but you should place your custom .whl file in `app/backend/`
3. **Permission errors on Linux/macOS**: Make sure the shell scripts are executable (`chmod +x *.sh`)
