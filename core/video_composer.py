import subprocess
from pathlib import Path
from typing import List

from pydub import AudioSegment


def compose_video(session_dir: Path, fps: int, audio_files: List[Path]) -> Path:
    try:
        mixed = AudioSegment.silent(duration=0)
        loaded = []
        for f in audio_files:
            if f.exists():
                loaded.append(AudioSegment.from_file(f))
        if loaded:
            max_len = max(len(a) for a in loaded)
            mixed = AudioSegment.silent(duration=max_len)
            for track in loaded:
                mixed = mixed.overlay(track)

        mixed_path = session_dir / "final_mixed_audio.wav"
        mixed.export(mixed_path, format="wav")

        rendered_dir = session_dir / "rendered_frames"
        output = session_dir / "final_output.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(rendered_dir / "frame_%06d.png"),
            "-i", str(mixed_path),
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", str(output),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output
    except Exception as exc:
        raise RuntimeError(f"compose_video failed: {exc}") from exc
