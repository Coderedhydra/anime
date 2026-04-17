from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO


def _iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    try:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        x1, y1 = max(ax1, bx1), max(ay1, by1)
        x2, y2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        if inter == 0:
            return 0.0
        aa = max(1, ax2 - ax1) * max(1, ay2 - ay1)
        bb = max(1, bx2 - bx1) * max(1, by2 - by1)
        return inter / (aa + bb - inter)
    except Exception:
        return 0.0


def _track_boxes(track_state: Dict[int, Tuple[int, int, int, int]], boxes: List[Tuple[int, int, int, int]], next_id: int):
    try:
        matches = {}
        used_tracks = set()
        used_boxes = set()
        for bi, box in enumerate(boxes):
            best_id, best_iou = None, 0.0
            for tid, tbox in track_state.items():
                if tid in used_tracks:
                    continue
                iou = _iou(box, tbox)
                if iou > best_iou:
                    best_id, best_iou = tid, iou
            if best_id is not None and best_iou > 0.2:
                matches[bi] = best_id
                used_tracks.add(best_id)
                used_boxes.add(bi)
        for bi, box in enumerate(boxes):
            if bi not in used_boxes:
                matches[bi] = next_id
                next_id += 1
        new_state = {matches[i]: box for i, box in enumerate(boxes)}
        return matches, new_state, next_id
    except Exception as exc:
        raise RuntimeError(f"Tracking failed: {exc}") from exc


def detect_and_track_characters(
    frame_paths: List[str],
    session_dir: Path,
    animated_hint: bool = False,
    stride: int = 5,
) -> Dict:
    try:
        pose_model = YOLO("yolov8n-pose.pt")
        det_model = YOLO("yolov8n.pt")
        tracks: Dict[int, Dict[int, Tuple[int, int, int, int]]] = defaultdict(dict)
        previews_dir = session_dir / "character_tracks"
        previews_dir.mkdir(parents=True, exist_ok=True)
        track_state = {}
        next_id = 0

        conf = 0.25 if animated_hint else 0.35
        iou_thr = 0.7 if animated_hint else 0.5

        for frame_idx, frame_path in enumerate(frame_paths, start=1):
            if frame_idx % stride != 0:
                continue
            img = cv2.imread(frame_path)
            if img is None:
                continue

            result_pose = pose_model.predict(source=img, conf=conf, iou=iou_thr, classes=[0], verbose=False)
            boxes = []
            for r in result_pose:
                if r.boxes is None:
                    continue
                for b in r.boxes.xyxy.cpu().numpy():
                    x1, y1, x2, y2 = [int(v) for v in b]
                    boxes.append((x1, y1, x2, y2))

            if animated_hint and len(boxes) == 0:
                result_det = det_model.predict(source=img, conf=0.2, iou=0.7, classes=[0], verbose=False)
                for r in result_det:
                    if r.boxes is None:
                        continue
                    for b in r.boxes.xyxy.cpu().numpy():
                        boxes.append(tuple(int(v) for v in b))

            if len(boxes) == 0:
                continue

            matches, track_state, next_id = _track_boxes(track_state, boxes, next_id)
            for bi, tid in matches.items():
                box = boxes[bi]
                tracks[tid][frame_idx] = box
                preview_file = previews_dir / f"char_{tid}.png"
                if not preview_file.exists():
                    x1, y1, x2, y2 = box
                    crop = img[max(0, y1):max(y1 + 1, y2), max(0, x1):max(x1 + 1, x2)]
                    if crop.size > 0:
                        Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)).save(preview_file)

        serializable = {int(cid): {int(f): list(b) for f, b in frames.items()} for cid, frames in tracks.items()}
        return {"tracks": serializable, "preview_dir": str(previews_dir), "character_count": len(serializable)}
    except Exception as exc:
        raise RuntimeError(f"detect_and_track_characters failed: {exc}") from exc
