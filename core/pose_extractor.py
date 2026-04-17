from pathlib import Path
from typing import Dict, List

import cv2
import mediapipe as mp

from core.utils import safe_json_dump

LANDMARK_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear", "mouth_left", "mouth_right", "left_shoulder", "right_shoulder", "left_elbow",
    "right_elbow", "left_wrist", "right_wrist", "left_pinky", "right_pinky", "left_index", "right_index",
    "left_thumb", "right_thumb", "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle",
    "left_heel", "right_heel", "left_foot_index", "right_foot_index",
]


def _empty_landmarks() -> Dict:
    try:
        return {name: {"x": 0.5, "y": 0.5, "z": 0.0, "vis": 0.0} for name in LANDMARK_NAMES}
    except Exception as exc:
        raise RuntimeError(f"Failed building empty landmark template: {exc}") from exc


def extract_pose_data(frame_paths: List[str], tracks: Dict, session_dir: Path) -> Dict:
    try:
        pose_dir = session_dir / "pose_data"
        pose_dir.mkdir(parents=True, exist_ok=True)
        pose = mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1)
        last_known: Dict[int, Dict] = {}
        counts = {}

        for char_id, frame_boxes in tracks.items():
            counts[int(char_id)] = 0
            for frame_idx, frame_path in enumerate(frame_paths, start=1):
                box = frame_boxes.get(str(frame_idx)) or frame_boxes.get(frame_idx)
                if box is None:
                    landmarks = last_known.get(int(char_id), _empty_landmarks())
                else:
                    img = cv2.imread(frame_path)
                    if img is None:
                        landmarks = last_known.get(int(char_id), _empty_landmarks())
                    else:
                        x1, y1, x2, y2 = [int(v) for v in box]
                        crop = img[max(0, y1):max(y2, y1 + 1), max(0, x1):max(x2, x1 + 1)]
                        if crop.size == 0:
                            landmarks = last_known.get(int(char_id), _empty_landmarks())
                        else:
                            result = pose.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                            if result.pose_landmarks:
                                landmarks = {}
                                for i, lm in enumerate(result.pose_landmarks.landmark):
                                    name = LANDMARK_NAMES[i]
                                    landmarks[name] = {
                                        "x": float(lm.x),
                                        "y": float(lm.y),
                                        "z": float(lm.z),
                                        "vis": float(lm.visibility),
                                    }
                                last_known[int(char_id)] = landmarks
                            else:
                                landmarks = last_known.get(int(char_id), _empty_landmarks())

                payload = {"frame": frame_idx, "char_id": int(char_id), "landmarks": landmarks}
                out = pose_dir / f"char_{char_id}_frame_{frame_idx:06d}.json"
                safe_json_dump(payload, out)
                counts[int(char_id)] += 1

        pose.close()
        return {"pose_dir": str(pose_dir), "frames_written": counts}
    except Exception as exc:
        raise RuntimeError(f"extract_pose_data failed: {exc}") from exc
