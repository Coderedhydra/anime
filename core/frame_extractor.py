import subprocess
from pathlib import Path
from typing import Dict, List

import cv2

from core.audio_extractor import extract_audio


def _get_fps(video_path: Path) -> float:
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError("Unable to open video")
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        cap.release()
        return float(fps)
    except Exception as exc:
        raise RuntimeError(f"Failed reading FPS: {exc}") from exc


def extract_frames_and_audio(video_path: Path, session_dir: Path) -> Dict:
    try:
        frames_dir = session_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        frame_pattern = frames_dir / "frame_%06d.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vsync",
            "0",
            str(frame_pattern),
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        frame_paths: List[str] = [str(p) for p in sorted(frames_dir.glob("frame_*.png"))]
        audio_path = extract_audio(video_path, session_dir / "audio_original.wav")
        fps = _get_fps(video_path)
        return {
            "frame_paths": frame_paths,
            "total_frames": len(frame_paths),
            "fps": fps,
            "audio_path": str(audio_path),
        }
    except Exception as exc:
        raise RuntimeError(f"extract_frames_and_audio failed: {exc}") from exc
