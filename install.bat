@echo off
setlocal

where py >nul 2>&1
if %errorlevel% neq 0 (
  echo Python launcher (py) not found. Please install Python 3.10+
  exit /b 1
)

py -3.10 -m venv .venv
if %errorlevel% neq 0 py -3 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python generate_assets.py

where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
  echo ffmpeg not found. Trying winget...
  winget install --id Gyan.FFmpeg -e || choco install ffmpeg -y
)

where ollama >nul 2>&1
if %errorlevel% neq 0 (
  echo Ollama not found. Install from https://ollama.com/download/windows
)

if not exist models\piper mkdir models\piper
if not exist models mkdir models
if not exist models\piper\en_US-amy-medium.onnx (
  powershell -Command "Invoke-WebRequest -Uri 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx' -OutFile 'models\\piper\\en_US-amy-medium.onnx'"
)
if not exist models\yolov8n-pose.pt (
  powershell -Command "Invoke-WebRequest -Uri 'https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n-pose.pt' -OutFile 'models\\yolov8n-pose.pt'"
)

echo ✅ AnimaForge ready! Run: python main.py
endlocal
