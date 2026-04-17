import io
import subprocess
from pathlib import Path
from typing import Dict, List

from pydub import AudioSegment

from config import PIPER_MODELS_DIR


def list_piper_voices() -> List[str]:
    try:
        return sorted([p.name for p in PIPER_MODELS_DIR.glob("*.onnx")])
    except Exception as exc:
        raise RuntimeError(f"list_piper_voices failed: {exc}") from exc


def list_coqui_voices() -> List[str]:
    try:
        return ["xtts_v2_default"]
    except Exception as exc:
        raise RuntimeError(f"list_coqui_voices failed: {exc}") from exc


def _change_speed(audio: AudioSegment, speed: float) -> AudioSegment:
    try:
        if abs(speed - 1.0) < 1e-3:
            return audio
        return audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * speed)}).set_frame_rate(audio.frame_rate)
    except Exception as exc:
        raise RuntimeError(f"Speed adjustment failed: {exc}") from exc


def _change_pitch(audio: AudioSegment, semitones: float) -> AudioSegment:
    try:
        if abs(semitones) < 1e-3:
            return audio
        rate = 2.0 ** (semitones / 12.0)
        return audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * rate)}).set_frame_rate(audio.frame_rate)
    except Exception as exc:
        raise RuntimeError(f"Pitch adjustment failed: {exc}") from exc


def _piper_synthesize(text: str, model_path: Path) -> AudioSegment:
    try:
        proc = subprocess.run(
            ["piper", "--model", str(model_path), "--output_raw"],
            input=text.encode("utf-8"),
            capture_output=True,
            check=True,
        )
        return AudioSegment.from_raw(io.BytesIO(proc.stdout), sample_width=2, frame_rate=22050, channels=1)
    except Exception as exc:
        raise RuntimeError(f"Piper synthesis failed: {exc}") from exc


def _coqui_synthesize(text: str) -> AudioSegment:
    try:
        from TTS.api import TTS

        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        wav = tts.tts(text=text)
        pcm = (bytes(int(max(-1.0, min(1.0, s)) * 32767).to_bytes(2, "little", signed=True) for s in wav))
        return AudioSegment.from_raw(io.BytesIO(pcm), sample_width=2, frame_rate=24000, channels=1)
    except Exception as exc:
        raise RuntimeError(f"Coqui synthesis failed: {exc}") from exc


def generate_character_audio(
    script_lines: List[Dict],
    char_id: int,
    engine: str,
    voice_name: str,
    pitch: float,
    speed: float,
    session_dir: Path,
) -> Path:
    try:
        timeline = AudioSegment.silent(duration=0)
        current_ms = 0
        for line in sorted(script_lines, key=lambda x: x["start"]):
            start_ms = int(line["start"] * 1000)
            if start_ms > current_ms:
                timeline += AudioSegment.silent(duration=start_ms - current_ms)
                current_ms = start_ms
            text = line.get("text", "").strip() or "..."
            if engine.lower().startswith("piper"):
                voice_path = PIPER_MODELS_DIR / voice_name
                audio = _piper_synthesize(text, voice_path)
            else:
                audio = _coqui_synthesize(text)
            audio = _change_pitch(_change_speed(audio, speed), pitch)
            timeline += audio
            current_ms = len(timeline)

        out = session_dir / f"new_audio_char{char_id}.wav"
        timeline.export(out, format="wav")
        return out
    except Exception as exc:
        raise RuntimeError(f"generate_character_audio failed for char {char_id}: {exc}") from exc
