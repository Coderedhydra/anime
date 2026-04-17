from pathlib import Path
import json

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
CHAR_DIR = ASSETS / "characters"
BG_DIR = ASSETS / "backgrounds"

CHARACTER_CONFIG = {
    "scale_factor": 0.7,
    "head_size_multiplier": 1.4,
    "limb_length_override": {
        "upper_arm": 60,
        "lower_arm": 55,
        "upper_leg": 70,
        "lower_leg": 65,
    },
    "canvas_height": 400,
    "canvas_width": 300,
}

PARTS = [
    "head",
    "head_happy",
    "head_sad",
    "head_angry",
    "mouth_A",
    "mouth_E",
    "mouth_I",
    "mouth_O",
    "mouth_U",
    "mouth_rest",
    "body",
    "upper_arm_L",
    "lower_arm_L",
    "hand_L",
    "upper_arm_R",
    "lower_arm_R",
    "hand_R",
    "upper_leg_L",
    "lower_leg_L",
    "foot_L",
    "upper_leg_R",
    "lower_leg_R",
    "foot_R",
]


def _part_size(part: str) -> tuple[int, int]:
    if part.startswith("head"):
        return 120, 120
    if part.startswith("mouth"):
        return 50, 20
    if part == "body":
        return 140, 200
    if "upper_arm" in part or "lower_arm" in part:
        return 28, 90
    if "upper_leg" in part or "lower_leg" in part:
        return 34, 100
    return 36, 36


def _draw_part(path: Path, color: tuple[int, int, int], label: str) -> None:
    size = _part_size(label)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((1, 1, size[0] - 2, size[1] - 2), radius=10, fill=color + (255,), outline=(15, 15, 15, 255), width=2)
    img.save(path)


def _draw_background(path: Path, title: str, base: tuple[int, int, int]) -> None:
    img = Image.new("RGB", (1920, 1080), base)
    dr = ImageDraw.Draw(img)
    dr.rectangle((80, 80, 1840, 1000), outline=(255, 255, 255), width=8)
    dr.text((120, 120), f"{title} placeholder", fill=(255, 255, 255))
    img.save(path)


def generate_assets() -> None:
    CHAR_DIR.mkdir(parents=True, exist_ok=True)
    BG_DIR.mkdir(parents=True, exist_ok=True)

    char_themes = {
        "puntoon_boy": (80, 150, 255),
        "puntoon_girl": (255, 120, 180),
    }
    mood_override = {
        "happy": (255, 215, 80),
        "sad": (120, 130, 200),
        "angry": (255, 90, 90),
    }

    for char_name, base_color in char_themes.items():
        cdir = CHAR_DIR / char_name
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "config.json").write_text(json.dumps(CHARACTER_CONFIG, indent=2), encoding="utf-8")
        for part in PARTS:
            color = base_color
            for mood, override in mood_override.items():
                if mood in part:
                    color = override
            _draw_part(cdir / f"{part}.png", color, part)

    backgrounds = {
        "classroom.png": (209, 178, 142),
        "park.png": (92, 179, 110),
        "home.png": (205, 166, 122),
        "street.png": (127, 127, 127),
        "night_sky.png": (25, 35, 80),
    }
    for filename, color in backgrounds.items():
        _draw_background(BG_DIR / filename, filename.replace(".png", ""), color)


if __name__ == "__main__":
    generate_assets()
    print("Generated placeholder assets under assets/")
