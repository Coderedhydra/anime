from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CORE_DIR = ROOT_DIR / "core"
ASSETS_DIR = ROOT_DIR / "assets"
CHARACTERS_DIR = ASSETS_DIR / "characters"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
MODELS_DIR = ROOT_DIR / "models"
WORKSPACE_DIR = ROOT_DIR / "workspace"

DEFAULT_WHISPER_MODEL = "base"
DEFAULT_TTS_ENGINE = "Piper"
DEFAULT_FPS = 24
DEFAULT_RESOLUTION = "1080p"
RESOLUTION_MAP = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4K": (3840, 2160),
}

YOLO_POSE_MODEL = MODELS_DIR / "yolov8n-pose.pt"
YOLO_DETECT_MODEL = "yolov8n.pt"
PIPER_MODELS_DIR = MODELS_DIR / "piper"
SESSION_PREFIX = "session_"

for directory in [MODELS_DIR, PIPER_MODELS_DIR, WORKSPACE_DIR, CHARACTERS_DIR, BACKGROUNDS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
