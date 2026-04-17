import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

import cv2
import yt_dlp


def _probe_video(video_path: Path) -> Dict:
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError("OpenCV failed to open video")
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        cap.release()
        duration = frames / fps if fps else 0
        return {
            "video_path": str(video_path),
            "video_title": video_path.stem,
            "duration": float(duration),
            "fps": float(fps),
            "resolution": f"{width}x{height}",
        }
    except Exception as exc:
        raise RuntimeError(f"Failed to inspect video metadata: {exc}") from exc


def _ffmpeg_normalize(input_path: Path, output_path: Path) -> None:
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    except Exception as exc:
        raise RuntimeError(f"Failed to normalize input video with ffmpeg: {exc}") from exc


def fetch_video(session_dir: Path, youtube_url: Optional[str] = None, local_file: Optional[str] = None) -> Dict:
    """Download or copy input video into session workspace as raw_video.mp4."""
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        output_path = session_dir / "raw_video.mp4"

        if youtube_url:
            ydl_opts = {
                "format": "bestvideo+bestaudio/best",
                "outtmpl": str(session_dir / "downloaded.%(ext)s"),
                "merge_output_format": "mp4",
                "noplaylist": True,
                "quiet": True,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(youtube_url, download=True)
                    downloaded = Path(ydl.prepare_filename(info)).with_suffix(".mp4")
                    if downloaded.exists():
                        shutil.move(str(downloaded), str(output_path))
                    else:
                        candidates = list(session_dir.glob("downloaded.*"))
                        if not candidates:
                            raise RuntimeError("yt-dlp completed but output file not found")
                        _ffmpeg_normalize(candidates[0], output_path)
                metadata = _probe_video(output_path)
                metadata["video_title"] = info.get("title") or metadata["video_title"]
                return metadata
            except yt_dlp.utils.DownloadError as exc:
                err = str(exc).lower()
                if "private" in err:
                    raise RuntimeError("YouTube video is private") from exc
                if "age" in err:
                    raise RuntimeError("YouTube video is age restricted") from exc
                if "unavailable" in err:
                    raise RuntimeError("YouTube video is unavailable") from exc
                raise RuntimeError(f"YouTube download failed: {exc}") from exc

        if local_file:
            src = Path(local_file)
            if not src.exists():
                raise FileNotFoundError(f"Local file not found: {src}")
            if src.suffix.lower() != ".mp4":
                _ffmpeg_normalize(src, output_path)
            else:
                shutil.copy2(src, output_path)
            return _probe_video(output_path)

        raise ValueError("Provide either youtube_url or local_file")
    except Exception as exc:
        raise RuntimeError(f"fetch_video failed: {exc}") from exc
