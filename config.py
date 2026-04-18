from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT / "workspace"
WORKSPACE.mkdir(parents=True, exist_ok=True)

DEFAULTS = {
    "fps": 24,
    "duration": 12,
    "resolution": "1280x720",
    "character_count": 3,
}

RESOLUTIONS = {
    "854x480": (854, 480),
    "1280x720": (1280, 720),
    "1920x1080": (1920, 1080),
}
