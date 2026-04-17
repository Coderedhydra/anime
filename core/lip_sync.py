from pathlib import Path
from typing import Dict, List

from pydub import AudioSegment

from core.utils import safe_json_dump


def _amp_to_mouth(amp: float, low: float, high: float) -> str:
    try:
        if amp <= low * 0.4:
            return "mouth_rest"
        if amp <= low:
            return "mouth_I" if int(amp) % 2 == 0 else "mouth_E"
        if amp <= high:
            return "mouth_A" if int(amp) % 2 == 0 else "mouth_O"
        return "mouth_U" if int(amp) % 2 == 0 else "mouth_O"
    except Exception as exc:
        raise RuntimeError(f"_amp_to_mouth failed: {exc}") from exc


def generate_lip_sync(audio_path: Path, char_id: int, fps: int, session_dir: Path) -> Path:
    try:
        audio = AudioSegment.from_file(audio_path)
        chunk_ms = 25
        amps = [audio[i:i + chunk_ms].rms for i in range(0, len(audio), chunk_ms)]
        low = sorted(amps)[max(0, len(amps) // 3)] if amps else 1
        high = sorted(amps)[max(0, (len(amps) * 2) // 3)] if amps else 2

        data: List[Dict] = []
        for i, amp in enumerate(amps, start=1):
            frame = int((i * chunk_ms / 1000.0) * fps) + 1
            data.append({"frame": frame, "mouth": _amp_to_mouth(float(amp), float(low), float(high))})

        out = session_dir / f"lip_sync_char{char_id}.json"
        safe_json_dump(data, out)
        return out
    except Exception as exc:
        raise RuntimeError(f"generate_lip_sync failed for char {char_id}: {exc}") from exc
