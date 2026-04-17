import subprocess
from pathlib import Path


def extract_audio(video_path: Path, output_audio_path: Path, sample_rate: int = 16000) -> Path:
    try:
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-acodec",
            "pcm_s16le",
            str(output_audio_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_audio_path
    except Exception as exc:
        raise RuntimeError(f"extract_audio failed: {exc}") from exc
