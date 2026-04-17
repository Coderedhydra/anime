import json
from pathlib import Path
from typing import Dict, List

import ollama

from core.utils import safe_json_dump


def get_available_models() -> List[str]:
    try:
        response = ollama.list()
        return [m.get("model") for m in response.get("models", []) if m.get("model")]
    except Exception as exc:
        raise RuntimeError(f"Failed to list Ollama models: {exc}") from exc


def _extract_json(text: str):
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            raise ValueError("No JSON array in Ollama response")
        return json.loads(text[start:end + 1])
    except Exception as exc:
        raise RuntimeError(f"Failed to parse JSON from model output: {exc}") from exc


def rewrite_script(transcript_json: List[Dict], char_names: Dict[str, str], style_prompt: str, model: str, output_path: Path) -> List[Dict]:
    try:
        system_prompt = (
            "You are a kids animation writer. Given this transcript with multiple speakers, rewrite it in an engaging kids "
            "cartoon style. Keep the exact same story, same timestamps, same speaker turns. Return only a valid JSON array "
            "with the same format."
        )
        prompt = {
            "char_names": char_names,
            "style": style_prompt,
            "transcript": transcript_json,
        }
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        )
        content = response["message"]["content"]
        rewritten = _extract_json(content)
        safe_json_dump(rewritten, output_path)
        return rewritten
    except Exception as exc:
        raise RuntimeError(f"rewrite_script failed: {exc}") from exc


def pick_background(scene_text: str, available_backgrounds: List[str], model: str) -> str:
    try:
        prompt = (
            f"Given this scene dialogue: '{scene_text}', which background fits best from this list: "
            f"{available_backgrounds}? Reply with just the filename."
        )
        response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        guess = response["message"]["content"].strip().splitlines()[0].strip()
        if guess in available_backgrounds:
            return guess
        return available_backgrounds[0]
    except Exception as exc:
        raise RuntimeError(f"pick_background failed: {exc}") from exc


def detect_emotion(text: str, model: str = "") -> str:
    try:
        text_lower = (text or "").lower()
        if any(w in text_lower for w in ["yay", "great", "happy", "love", "awesome"]):
            return "happy"
        if any(w in text_lower for w in ["sad", "sorry", "cry", "upset"]):
            return "sad"
        if any(w in text_lower for w in ["angry", "mad", "hate", "furious"]):
            return "angry"
        if any(w in text_lower for w in ["wow", "what", "surprise", "omg"]):
            return "surprised"
        return "neutral"
    except Exception as exc:
        raise RuntimeError(f"detect_emotion failed: {exc}") from exc
