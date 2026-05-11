#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --clean --windowed --onefile --name presence-desktop app.py

echo
echo "Linux build is ready:"
echo "$(pwd)/dist/presence-desktop"
