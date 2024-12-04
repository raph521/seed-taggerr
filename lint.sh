#!/usr/bin/env bash

set -euo pipefail

# Create virtual environment and activate it
python3 -m venv env
source env/bin/activate

# Install dependencies
python3 -m pip install --no-cache-dir -r dev-requirements.txt

# Lint and type check
ruff format app/*.py
ruff check app/*.py
mypy app/*.py
shellcheck app/*.sh
hadolintw Dockerfile --ignore DL3018
