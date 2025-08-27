 #!/bin/sh

if [ ! -d ".venv" ]; then
    echo 'Creating Python virtual environment ".venv"...'
    python3 -m venv .venv
else
    echo 'Virtual environment ".venv" already exists, skipping creation'
fi

echo 'Installing dependencies from "requirements.txt" into virtual environment (in quiet mode)...'
.venv/bin/python -m pip --quiet --disable-pip-version-check install -r app/backend/requirements.txt
