from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from scipy.signal import savgol_filter

from core.utils import safe_json_dump, safe_json_load


def smooth_character_motion(pose_dir: Path, char_id: int) -> Path:
    try:
        files = sorted(pose_dir.glob(f"char_{char_id}_frame_*.json"))
        if not files:
            raise FileNotFoundError(f"No pose files for char {char_id}")

        frames = [safe_json_load(p) for p in files]
        landmarks = defaultdict(lambda: {"x": [], "y": [], "z": [], "vis": []})
        for frame in frames:
            for name, vals in frame["landmarks"].items():
                landmarks[name]["x"].append(vals["x"])
                landmarks[name]["y"].append(vals["y"])
                landmarks[name]["z"].append(vals.get("z", 0.0))
                landmarks[name]["vis"].append(vals.get("vis", 0.0))

        win = 11 if len(frames) >= 11 else max(3, len(frames) // 2 * 2 + 1)
        poly = 3 if win > 3 else 2
        smoothed: List[Dict] = []
        for idx, frame in enumerate(frames):
            new_lm = {}
            for name, series in landmarks.items():
                sx = savgol_filter(series["x"], window_length=win, polyorder=poly, mode="nearest")
                sy = savgol_filter(series["y"], window_length=win, polyorder=poly, mode="nearest")
                new_lm[name] = {
                    "x": float(sx[idx]),
                    "y": float(sy[idx]),
                    "z": float(series["z"][idx]),
                    "vis": float(series["vis"][idx]),
                }
            smoothed.append({"frame": frame["frame"], "char_id": char_id, "landmarks": new_lm})

        out = pose_dir / "smoothed" / f"char_{char_id}_all_frames.json"
        safe_json_dump(smoothed, out)
        return out
    except Exception as exc:
        raise RuntimeError(f"smooth_character_motion failed for char {char_id}: {exc}") from exc
