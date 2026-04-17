from pathlib import Path
from typing import Dict, List

import numpy as np
from faster_whisper import WhisperModel
from pydub import AudioSegment

from core.utils import safe_json_dump


def _segment_energy_map(audio_path: Path, window_ms: int = 100) -> List[float]:
    try:
        audio = AudioSegment.from_file(audio_path)
        vals = []
        for i in range(0, len(audio), window_ms):
            chunk = audio[i:i + window_ms]
            vals.append(float(chunk.rms))
        return vals
    except Exception as exc:
        raise RuntimeError(f"Energy map creation failed: {exc}") from exc


def transcribe_and_diarize(audio_path: Path, session_dir: Path, whisper_model_size: str = "base") -> Dict:
    try:
        model = WhisperModel(whisper_model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(audio_path), vad_filter=True)

        transcript = []
        for seg in segments:
            transcript.append(
                {
                    "start": float(seg.start),
                    "end": float(seg.end),
                    "speaker": "SPEAKER_0",
                    "text": (seg.text or "").strip(),
                }
            )

        # Simple local diarization fallback: alternate speakers on long pauses/energy change.
        energies = _segment_energy_map(audio_path)
        if transcript:
            speaker = 0
            prev_end = transcript[0]["start"]
            for item in transcript:
                gap = item["start"] - prev_end
                idx = int(item["start"] * 10)
                e = energies[idx] if 0 <= idx < len(energies) else 0.0
                if gap > 0.8 or e < np.percentile(energies, 25):
                    speaker = (speaker + 1) % 2
                item["speaker"] = f"SPEAKER_{speaker}"
                prev_end = item["end"]

        out = session_dir / "transcript.json"
        safe_json_dump(transcript, out)
        return {
            "transcript_path": str(out),
            "speaker_count": len(set(item["speaker"] for item in transcript)) if transcript else 0,
            "transcript": transcript,
        }
    except Exception as exc:
        raise RuntimeError(f"transcribe_and_diarize failed: {exc}") from exc


def map_speakers_to_characters(transcript: List[Dict], mouth_motion_scores: Dict[int, Dict[int, float]]) -> Dict[str, int]:
    try:
        mapping = {}
        for speaker in sorted(set(item["speaker"] for item in transcript)):
            scored = []
            for char_id, frame_scores in mouth_motion_scores.items():
                score = 0.0
                for seg in transcript:
                    if seg["speaker"] != speaker:
                        continue
                    start_f = int(seg["start"] * 24)
                    end_f = int(seg["end"] * 24)
                    score += sum(frame_scores.get(i, 0.0) for i in range(start_f, end_f + 1))
                scored.append((score, char_id))
            best_char = max(scored)[1] if scored else 0
            mapping[speaker] = int(best_char)
        return mapping
    except Exception as exc:
        raise RuntimeError(f"map_speakers_to_characters failed: {exc}") from exc
