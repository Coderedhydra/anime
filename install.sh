#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN=${PYTHON_BIN:-python3.10}
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN=python3
fi

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg missing. Installing with apt (if available)..."
  if command -v apt >/dev/null 2>&1; then
    sudo apt update && sudo apt install -y ffmpeg
  else
    echo "Please install ffmpeg manually."
  fi
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Install Ollama: https://ollama.com/download"
fi

echo "✅ Ready. Run: python main.py"
