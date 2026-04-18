import math
import random
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple
from uuid import uuid4

import numpy as np
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from PIL import Image, ImageDraw

from config import WORKSPACE


def _draw_background(draw: ImageDraw.ImageDraw, width: int, height: int, bg_rgb: List[int]) -> None:
    try:
        r, g, b = [int(max(0, min(255, v))) for v in bg_rgb]
        for y in range(height):
            factor = y / max(1, height)
            color = (int(r * (0.8 + 0.2 * factor)), int(g * (0.8 + 0.2 * factor)), int(b * (0.8 + 0.2 * factor)))
            draw.line([(0, y), (width, y)], fill=color)
        draw.rectangle((0, int(height * 0.78), width, height), fill=(60, 160, 90))
    except Exception as exc:
        raise RuntimeError(f"_draw_background failed: {exc}") from exc


def _rig_pose(action: str, t: float) -> Dict[str, float]:
    try:
        phase = math.sin(t * 4.0)
        if action == "jump":
            return {"bob": abs(math.sin(t * 6.0)) * -40, "arm": phase * 45, "leg": phase * 30}
        if action == "run":
            return {"bob": abs(math.sin(t * 8.0)) * -20, "arm": phase * 65, "leg": -phase * 65}
        if action == "wave":
            return {"bob": 0, "arm": math.sin(t * 8.0) * 80, "leg": 8}
        if action == "walk":
            return {"bob": 0, "arm": phase * 30, "leg": -phase * 30}
        return {"bob": 0, "arm": 8, "leg": 8}
    except Exception as exc:
        raise RuntimeError(f"_rig_pose failed: {exc}") from exc


def _draw_rig_character(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, name: str, action: str, mood: str, t: float) -> None:
    try:
        pose = _rig_pose(action, t)
        bob = int(pose["bob"])
        head_r = max(10, size // 5)
        body_h = size // 2
        skin = (255, 230, 180)
        outfit_seed = abs(hash(name)) % 255
        outfit = ((outfit_seed + 70) % 255, (outfit_seed + 130) % 255, (outfit_seed + 200) % 255)

        hx, hy = x, y - body_h - head_r + bob
        draw.ellipse((hx - head_r, hy - head_r, hx + head_r, hy + head_r), fill=skin, outline=(20, 20, 20), width=2)
        draw.line((x, y - body_h + bob, x, y + bob), fill=outfit, width=8)

        arm_a = math.radians(pose["arm"])
        arm_len = size // 3
        l_ax = x - int(math.cos(arm_a) * arm_len)
        l_ay = y - body_h // 2 + int(math.sin(arm_a) * arm_len) + bob
        r_ax = x + int(math.cos(arm_a) * arm_len)
        r_ay = y - body_h // 2 - int(math.sin(arm_a) * arm_len) + bob
        draw.line((x, y - body_h // 2 + bob, l_ax, l_ay), fill=outfit, width=6)
        draw.line((x, y - body_h // 2 + bob, r_ax, r_ay), fill=outfit, width=6)

        leg_a = math.radians(pose["leg"])
        leg_len = size // 3
        l_lx = x - int(math.sin(leg_a) * leg_len)
        l_ly = y + int(math.cos(leg_a) * leg_len) + bob
        r_lx = x + int(math.sin(leg_a) * leg_len)
        r_ly = y + int(math.cos(leg_a) * leg_len) + bob
        draw.line((x, y + bob, l_lx, l_ly), fill=(40, 40, 40), width=7)
        draw.line((x, y + bob, r_lx, r_ly), fill=(40, 40, 40), width=7)

        mouth = "🙂" if mood == "happy" else "😮" if mood == "surprised" else "😐"
        draw.text((hx - head_r, hy + head_r + 10), f"{name} {mouth}", fill=(15, 15, 15))
    except Exception as exc:
        raise RuntimeError(f"_draw_rig_character failed: {exc}") from exc


def _save_character_pngs(session_dir: Path, character_names: List[str]) -> None:
    try:
        chars_dir = session_dir / "characters"
        chars_dir.mkdir(parents=True, exist_ok=True)
        for name in character_names:
            img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            _draw_rig_character(d, 128, 190, 140, name, "idle", "happy", 0.0)
            img.save(chars_dir / f"{name.replace(' ', '_').lower()}.png")
    except Exception as exc:
        raise RuntimeError(f"_save_character_pngs failed: {exc}") from exc


def render_animation(
    story: str,
    storyboard: List[Dict],
    duration: int,
    fps: int,
    resolution: Tuple[int, int],
    progress_fn=None,
) -> Dict[str, str]:
    try:
        session_dir = WORKSPACE / f"session_{uuid4().hex[:8]}"
        frames_dir = session_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        width, height = resolution
        total_frames = duration * fps

        all_names = []
        for sc in storyboard:
            for c in sc.get("characters", []):
                if c.get("name") and c["name"] not in all_names:
                    all_names.append(c["name"])
        all_names = all_names or ["Hero"]
        _save_character_pngs(session_dir, all_names)

        frame_paths = []
        for f in range(total_frames):
            t = f / fps
            scene = next((s for s in storyboard if s.get("start", 0) <= t < s.get("end", duration + 1)), storyboard[-1])
            img = Image.new("RGB", (width, height), (0, 0, 0))
            draw = ImageDraw.Draw(img)
            _draw_background(draw, width, height, scene.get("background", [120, 160, 220]))

            chars = scene.get("characters", [])
            spacing = width // (len(chars) + 1) if chars else width // 2
            ground_y = int(height * 0.78)
            for i, c in enumerate(chars):
                base_x = spacing * (i + 1)
                offset = int(math.sin(t * 1.5 + i) * 20)
                _draw_rig_character(
                    draw,
                    base_x + offset,
                    ground_y,
                    max(120, height // 4),
                    c.get("name", f"Char{i+1}"),
                    c.get("action", "idle"),
                    c.get("mood", "happy"),
                    t,
                )

            dialogue = scene.get("dialogue", "")
            if dialogue:
                wrapped = "\n".join(textwrap.wrap(dialogue, width=50)[:3])
                draw.rounded_rectangle((30, 20, width - 30, 140), radius=16, fill=(255, 255, 255), outline=(0, 0, 0), width=3)
                draw.text((48, 42), wrapped, fill=(10, 10, 10))

            out = frames_dir / f"frame_{f:06d}.png"
            img.save(out)
            frame_paths.append(str(out))
            if progress_fn and f % max(1, fps // 2) == 0:
                progress_fn(f / max(1, total_frames), f"Rendering frame {f}/{total_frames}")

        video_path = session_dir / "final_output.mp4"
        clip = ImageSequenceClip(frame_paths, fps=fps)
        clip.write_videofile(str(video_path), codec="libx264", audio=False, logger=None)
        if progress_fn:
            progress_fn(1.0, "Done")

        return {
            "session_dir": str(session_dir),
            "video_path": str(video_path),
            "characters_dir": str(session_dir / "characters"),
        }
    except Exception as exc:
        raise RuntimeError(f"render_animation failed: {exc}") from exc
