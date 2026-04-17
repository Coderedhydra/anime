import json
import logging
import threading
from pathlib import Path
from typing import Any


def setup_logger(session_dir: Path) -> logging.Logger:
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger(f"animaforge_{session_dir.name}")
        logger.setLevel(logging.INFO)
        if logger.handlers:
            return logger
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        file_handler = logging.FileHandler(session_dir / "session.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        return logger
    except Exception as exc:
        raise RuntimeError(f"Failed to setup logger: {exc}") from exc


def safe_json_dump(data: Any, path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"Failed to write JSON to {path}: {exc}") from exc


def safe_json_load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to load JSON {path}: {exc}") from exc


def run_in_thread(target, *args, **kwargs) -> threading.Thread:
    try:
        thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread
    except Exception as exc:
        raise RuntimeError(f"Failed to start thread: {exc}") from exc
