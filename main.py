import shutil
import socket

from ui import build_app


def _check_ffmpeg() -> bool:
    try:
        return shutil.which("ffmpeg") is not None
    except Exception:
        return False


def _check_ollama() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=1.5):
            return True
    except Exception:
        return False


def run() -> None:
    print("╔════════════════════════════════════╗")
    print("║ Text2Toon Studio - Story to 2D MP4 ║")
    print("╚════════════════════════════════════╝")
    print(f"FFmpeg: {'OK' if _check_ffmpeg() else 'MISSING'}")
    print(f"Ollama: {'RUNNING' if _check_ollama() else 'NOT RUNNING'}")

    app = build_app()
    app.queue(default_concurrency_limit=2)
    app.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    run()
