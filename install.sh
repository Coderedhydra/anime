#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN=${PYTHON_BIN:-python3.10}
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN=python3
fi

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python generate_assets.py

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found. Installing via apt..."
  if command -v apt >/dev/null 2>&1; then
    sudo apt update && sudo apt install -y ffmpeg
  else
    echo "Please install ffmpeg manually for your OS."
  fi
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found. Install from: https://ollama.com/download"
fi

mkdir -p models/piper models
if [ ! -f models/piper/en_US-amy-medium.onnx ]; then
  curl -L -o models/piper/en_US-amy-medium.onnx https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
fi

if [ ! -f models/yolov8n-pose.pt ]; then
  curl -L -o models/yolov8n-pose.pt https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n-pose.pt
fi

echo "✅ AnimaForge ready! Run: python main.py"
