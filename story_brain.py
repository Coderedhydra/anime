import json
import re
import subprocess
from typing import Dict, List


def list_ollama_models() -> List[str]:
    try:
        proc = subprocess.run(["ollama", "list"], check=True, capture_output=True, text=True)
        lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        if len(lines) <= 1:
            return []
        return [ln.split()[0] for ln in lines[1:]]
    except Exception:
        return []


def _extract_json(text: str):
    try:
        m = re.search(r"\[.*\]", text, flags=re.S)
        if not m:
            raise ValueError("No JSON array found")
        return json.loads(m.group(0))
    except Exception:
        return None


def default_storyboard(story: str, duration: int, character_count: int) -> List[Dict]:
    try:
        names = [f"Char{i+1}" for i in range(character_count)]
        segment = max(2.0, duration / 3)
        scenes = []
        for i in range(3):
            scenes.append(
                {
                    "start": round(i * segment, 2),
                    "end": round(min(duration, (i + 1) * segment), 2),
                    "background": [20 + i * 40, 110 + i * 30, 180 - i * 20],
                    "dialogue": story[:200],
                    "characters": [
                        {"name": nm, "action": "walk" if i % 2 == 0 else "wave", "mood": "happy"}
                        for nm in names
                    ],
                }
            )
        return scenes
    except Exception as exc:
        raise RuntimeError(f"default_storyboard failed: {exc}") from exc


def generate_storyboard_with_ollama(story: str, model: str, duration: int, character_count: int) -> List[Dict]:
    try:
        import ollama

        prompt = f"""
You are a 2D animation director.
Create a JSON ARRAY of scenes only.
Input story: {story}
Total duration seconds: {duration}
Characters: {character_count}
Each scene item must have keys:
start, end, background (RGB array), dialogue, characters
characters is array of objects with keys: name, action, mood.
Actions allowed: walk, jump, wave, idle, run.
Keep valid JSON only.
""".strip()
        res = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        content = res.get("message", {}).get("content", "")
        parsed = _extract_json(content)
        if not parsed:
            return default_storyboard(story, duration, character_count)
        return parsed
    except Exception:
        return default_storyboard(story, duration, character_count)
