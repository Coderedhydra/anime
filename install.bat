@echo off
setlocal

where py >nul 2>&1
if %errorlevel% neq 0 (
  echo Please install Python 3.10+ first.
  exit /b 1
)

py -3.10 -m venv .venv
if %errorlevel% neq 0 py -3 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
  echo Installing ffmpeg via winget/choco...
  winget install --id Gyan.FFmpeg -e || choco install ffmpeg -y
)

where ollama >nul 2>&1
if %errorlevel% neq 0 (
  echo Install Ollama: https://ollama.com/download/windows
)

echo ✅ Ready. Run: python main.py
endlocal
