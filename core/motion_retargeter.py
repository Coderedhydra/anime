import math
from pathlib import Path
from typing import Dict, List, Tuple

from core.utils import safe_json_dump, safe_json_load


PAIRS = {
    "upper_arm_L": ("left_shoulder", "left_elbow"),
    "lower_arm_L": ("left_elbow", "left_wrist"),
    "upper_arm_R": ("right_shoulder", "right_elbow"),
    "lower_arm_R": ("right_elbow", "right_wrist"),
    "upper_leg_L": ("left_hip", "left_knee"),
    "lower_leg_L": ("left_knee", "left_ankle"),
    "upper_leg_R": ("right_hip", "right_knee"),
    "lower_leg_R": ("right_knee", "right_ankle"),
}


def _angle(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    try:
        return math.degrees(math.atan2(b[1] - a[0], b[0] - a[0]))
    except Exception as exc:
        raise RuntimeError(f"Angle calculation failed: {exc}") from exc


def retarget_motion(smoothed_json: Path, character_config_path: Path, out_path: Path) -> Path:
    try:
        frames: List[Dict] = safe_json_load(smoothed_json)
        cfg = safe_json_load(character_config_path)
        cw = int(cfg.get("canvas_width", 300))
        ch = int(cfg.get("canvas_height", 400))
        scale = float(cfg.get("scale_factor", 0.7))

        retargeted = []
        for frame in frames:
            lm = frame["landmarks"]
            part_map = {}
            for part, (s_name, e_name) in PAIRS.items():
                s = lm[s_name]
                e = lm[e_name]
                sx, sy = s["x"] * cw * scale, s["y"] * ch * scale
                ex, ey = e["x"] * cw * scale, e["y"] * ch * scale
                part_map[part] = {"x": float(sx), "y": float(sy), "angle": float(_angle((sx, sy), (ex, ey)))}
            part_map["body"] = {"x": float(lm["left_hip"]["x"] * cw * scale), "y": float(lm["left_hip"]["y"] * ch * scale), "angle": 0.0}
            part_map["head"] = {"x": float(lm["nose"]["x"] * cw * scale), "y": float(lm["nose"]["y"] * ch * scale), "angle": 0.0}
            retargeted.append({"frame": frame["frame"], "char_id": frame["char_id"], "parts": part_map})

        safe_json_dump(retargeted, out_path)
        return out_path
    except Exception as exc:
        raise RuntimeError(f"retarget_motion failed: {exc}") from exc
