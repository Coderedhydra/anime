import shutil
import socket
from pathlib import Path

import config
from ui import build_ui, scan_ollama_models


def check_ffmpeg() -> bool:
    try:
        return shutil.which("ffmpeg") is not None
    except Exception as exc:
        raise RuntimeError(f"FFmpeg check failed: {exc}") from exc


def check_ollama_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=1.5):
            return True
    except Exception:
        return False


def startup_checks() -> None:
    try:
        config.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        ffmpeg_ok = check_ffmpeg()
        ollama_ok = check_ollama_running()
        models, _ = scan_ollama_models()
        print(f"[AnimaForge] FFmpeg: {'OK' if ffmpeg_ok else 'MISSING'}")
        print(f"[AnimaForge] Ollama daemon: {'OK' if ollama_ok else 'NOT RUNNING'}")
        print(f"[AnimaForge] Ollama models found: {len(models)}")
    except Exception as exc:
        print(f"[AnimaForge] Startup warning: {exc}")


def print_banner() -> None:
    try:
        print("╔══════════════════════════╗")
        print("║   AnimaForge v1.0 🎬    ║")
        print("║   http://localhost:7860  ║")
        print("╚══════════════════════════╝")
    except Exception as exc:
        raise RuntimeError(f"Failed printing banner: {exc}") from exc


if __name__ == "__main__":
    try:
        startup_checks()
        print_banner()
        app = build_ui()
        app.queue(default_concurrency_limit=2)
        app.launch(server_name="127.0.0.1", server_port=7860)
    except Exception as exc:
        print(f"Fatal error while launching AnimaForge: {exc}")
