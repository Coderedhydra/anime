from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

from config import BACKGROUNDS_DIR
from core import brain
from core.utils import safe_json_load


def list_backgrounds() -> List[str]:
    try:
        return sorted([p.name for p in BACKGROUNDS_DIR.glob("*.png")])
    except Exception as exc:
        raise RuntimeError(f"list_backgrounds failed: {exc}") from exc


def get_background_for_scene(
    scene_text: str,
    mode: str,
    ollama_model: str,
    selected_background: Optional[str] = None,
    scene_bg_map_path: Optional[Path] = None,
    scene_id: Optional[str] = None,
) -> str:
    try:
        backgrounds = list_backgrounds()
        if not backgrounds:
            raise RuntimeError("No background assets found")
        if mode.lower().startswith("auto"):
            return brain.pick_background(scene_text, backgrounds, ollama_model)
        if mode.lower().startswith("single"):
            return selected_background or backgrounds[0]
        if mode.lower().startswith("manual"):
            if not scene_bg_map_path or not scene_bg_map_path.exists() or not scene_id:
                return backgrounds[0]
            mapping: Dict = safe_json_load(scene_bg_map_path)
            return mapping.get(scene_id, backgrounds[0])
        return backgrounds[0]
    except Exception as exc:
        raise RuntimeError(f"get_background_for_scene failed: {exc}") from exc


def load_background(filename: str, width: int, height: int) -> Image.Image:
    try:
        path = BACKGROUNDS_DIR / filename
        if not path.exists():
            return Image.new("RGBA", (width, height), (120, 180, 255, 255))
        return Image.open(path).convert("RGBA").resize((width, height))
    except Exception as exc:
        raise RuntimeError(f"load_background failed: {exc}") from exc
