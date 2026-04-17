from pathlib import Path
from typing import Dict, List

from PIL import Image

from core.utils import safe_json_load

DRAW_ORDER = [
    "upper_leg_L", "lower_leg_L", "foot_L",
    "upper_leg_R", "lower_leg_R", "foot_R",
    "body",
    "upper_arm_L", "lower_arm_L", "hand_L",
    "upper_arm_R", "lower_arm_R", "hand_R",
]


def _load_parts(character_dir: Path) -> Dict[str, Image.Image]:
    try:
        parts = {}
        for p in character_dir.glob("*.png"):
            parts[p.stem] = Image.open(p).convert("RGBA")
        return parts
    except Exception as exc:
        raise RuntimeError(f"Failed loading character parts from {character_dir}: {exc}") from exc


def render_frames(
    retargeted_per_char: Dict[int, Path],
    character_assignments: Dict[int, Path],
    lip_sync_per_char: Dict[int, Path],
    emotions_per_frame: Dict[int, Dict[int, str]],
    background_frames: Dict[int, Image.Image],
    output_resolution: tuple,
    session_dir: Path,
    progress_callback=None,
) -> Path:
    try:
        rendered = session_dir / "rendered_frames"
        rendered.mkdir(parents=True, exist_ok=True)

        rig_data = {cid: safe_json_load(path) for cid, path in retargeted_per_char.items()}
        lip_data = {cid: safe_json_load(path) for cid, path in lip_sync_per_char.items()}
        lips_by_frame = {cid: {d["frame"]: d["mouth"] for d in arr} for cid, arr in lip_data.items()}
        assets = {cid: _load_parts(character_assignments[cid]) for cid in character_assignments}

        total_frames = max((d[-1]["frame"] for d in rig_data.values() if d), default=0)
        for frame_idx in range(1, total_frames + 1):
            bg = background_frames.get(frame_idx)
            if bg is None:
                bg = Image.new("RGBA", output_resolution, (135, 206, 235, 255))
            else:
                bg = bg.resize(output_resolution)

            draw_list = []
            for cid, entries in rig_data.items():
                match = next((e for e in entries if e["frame"] == frame_idx), None)
                if match:
                    draw_list.append((match["parts"].get("body", {}).get("y", 0), cid, match))
            draw_list.sort(key=lambda x: x[0])

            for _, cid, entry in draw_list:
                parts = assets[cid]
                canvas = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
                pm = entry["parts"]
                for part_name in DRAW_ORDER:
                    sprite = parts.get(part_name)
                    if sprite is None:
                        continue
                    pd = pm.get(part_name, {"x": 120, "y": 200, "angle": 0})
                    rot = sprite.rotate(pd["angle"], expand=True)
                    canvas.paste(rot, (int(pd["x"]), int(pd["y"])), rot)

                emotion = emotions_per_frame.get(cid, {}).get(frame_idx, "neutral")
                head_key = f"head_{emotion}" if f"head_{emotion}" in parts else "head"
                mouth_key = lips_by_frame.get(cid, {}).get(frame_idx, "mouth_rest")
                head = parts.get(head_key, parts.get("head"))
                mouth = parts.get(mouth_key, parts.get("mouth_rest"))
                hx, hy = int(pm.get("head", {}).get("x", 140)), int(pm.get("head", {}).get("y", 80))
                if head:
                    canvas.paste(head, (hx, hy), head)
                if mouth:
                    canvas.paste(mouth, (hx + 25, hy + 55), mouth)

                bg.paste(canvas, (int(hx * 2), int(hy * 2)), canvas)

            out = rendered / f"frame_{frame_idx:06d}.png"
            bg.convert("RGB").save(out)
            if progress_callback and frame_idx % 50 == 0:
                progress_callback(frame_idx, total_frames, str(out))

        return rendered
    except Exception as exc:
        raise RuntimeError(f"render_frames failed: {exc}") from exc
