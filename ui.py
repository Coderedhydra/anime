import json
import queue
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, Tuple
from uuid import uuid4

import gradio as gr
from PIL import Image

import config
from core.background_manager import get_background_for_scene, list_backgrounds, load_background
from core.brain import get_available_models, rewrite_script, detect_emotion
from core.character_detector import detect_and_track_characters
from core.downloader import fetch_video
from core.frame_extractor import extract_frames_and_audio
from core.lip_sync import generate_lip_sync
from core.motion_retargeter import retarget_motion
from core.motion_smoother import smooth_character_motion
from core.pose_extractor import extract_pose_data
from core.transcriber import map_speakers_to_characters, transcribe_and_diarize
from core.tts_generator import generate_character_audio, list_coqui_voices, list_piper_voices
from core.utils import run_in_thread, safe_json_dump, safe_json_load, setup_logger
from core.video_composer import compose_video
from core.character_renderer import render_frames

STATE = {
    "settings": {
        "ollama_model": "",
        "whisper_model": config.DEFAULT_WHISPER_MODEL,
        "tts_engine": config.DEFAULT_TTS_ENGINE,
        "fps": config.DEFAULT_FPS,
        "resolution": config.DEFAULT_RESOLUTION,
    },
    "session_dir": None,
    "analysis": {},
}


def _is_ollama_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=1.5):
            return True
    except Exception:
        return False


def scan_ollama_models() -> Tuple[list, str]:
    try:
        models = []
        try:
            proc = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
            lines = [l.strip() for l in proc.stdout.splitlines()[1:] if l.strip()]
            models = [l.split()[0] for l in lines if l]
        except Exception:
            models = get_available_models()
        status = "✅ Ollama Running" if _is_ollama_running() else "❌ Ollama Not Found"
        return models, status
    except Exception as exc:
        return [], f"❌ Ollama check error: {exc}"


def save_settings(ollama_model, whisper_model, tts_engine, fps, resolution):
    try:
        STATE["settings"] = {
            "ollama_model": ollama_model,
            "whisper_model": whisper_model,
            "tts_engine": tts_engine,
            "fps": int(fps),
            "resolution": resolution,
        }
        return "Settings saved ✅"
    except Exception as exc:
        return f"Failed to save settings: {exc}"


def _new_session() -> Path:
    try:
        sid = f"{config.SESSION_PREFIX}{uuid4().hex[:8]}"
        session_dir = config.WORKSPACE_DIR / sid
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    except Exception as exc:
        raise RuntimeError(f"Session creation failed: {exc}") from exc


def download_and_analyze(youtube_url, local_video, progress=gr.Progress()):
    try:
        session_dir = _new_session()
        logger = setup_logger(session_dir)
        STATE["session_dir"] = session_dir
        logs = []

        progress(0.05, desc="Loading input video")
        local_file = getattr(local_video, "name", None) if local_video else None
        meta = fetch_video(session_dir, youtube_url=youtube_url.strip() or None, local_file=local_file)
        logs.append("✅ Video loaded")
        logger.info(logs[-1])

        progress(0.25, desc="Extracting frames/audio")
        fa = extract_frames_and_audio(Path(meta["video_path"]), session_dir)
        logs.append("✅ Frames extracted")

        progress(0.45, desc="Detecting characters")
        animated_hint = "anime" in (meta.get("video_title", "").lower()) or "cartoon" in (meta.get("video_title", "").lower())
        cd = detect_and_track_characters(fa["frame_paths"], session_dir, animated_hint=animated_hint)
        logs.append(f"✅ Characters detected: {cd['character_count']}")

        progress(0.65, desc="Extracting pose")
        pose = extract_pose_data(fa["frame_paths"], cd["tracks"], session_dir)
        logs.append("✅ Pose extraction complete")

        progress(0.85, desc="Transcribing audio")
        transcript_result = transcribe_and_diarize(Path(fa["audio_path"]), session_dir, STATE["settings"]["whisper_model"])
        logs.append("✅ Transcript created")

        thumbnail = fa["frame_paths"][0] if fa["frame_paths"] else None
        analysis = {
            "meta": meta,
            "frames": fa,
            "chars": cd,
            "pose": pose,
            "transcript": transcript_result,
            "logs": logs,
            "thumbnail": thumbnail,
        }
        STATE["analysis"] = analysis
        progress(1.0, desc="Done")
        return (
            thumbnail,
            f"{meta['duration']:.2f}s",
            f"{meta['fps']:.2f}",
            str(cd["character_count"]),
            str(transcript_result["speaker_count"]),
            "\n".join(logs),
            json.dumps(transcript_result["transcript"], indent=2),
        )
    except Exception as exc:
        return None, "0", "0", "0", "0", f"❌ {exc}", "[]"


def rewrite_with_ollama(raw_transcript_text):
    try:
        transcript = json.loads(raw_transcript_text)
        session_dir = Path(STATE["session_dir"])
        rewritten = rewrite_script(
            transcript,
            {"SPEAKER_0": "Alex", "SPEAKER_1": "Sam"},
            "Playful and educational",
            STATE["settings"]["ollama_model"],
            session_dir / "new_script.json",
        )
        return json.dumps(rewritten, indent=2)
    except Exception as exc:
        return f"[]\n# rewrite failed: {exc}"


def generate_animation(
    rewritten_script_text,
    background_mode,
    single_background,
    progress=gr.Progress(),
):
    try:
        session_dir = Path(STATE["session_dir"])
        analysis = STATE["analysis"]
        fps = int(STATE["settings"]["fps"])
        w, h = config.RESOLUTION_MAP[STATE["settings"]["resolution"]]
        q = queue.Queue()
        outputs = {"video": None, "stats": "", "logs": ""}

        def worker():
            try:
                logs = []
                transcript = json.loads(rewritten_script_text)
                speaker_ids = sorted(set(t["speaker"] for t in transcript))
                char_ids = sorted(int(c) for c in analysis["chars"]["tracks"].keys()) or [0]

                mouth_motion = {cid: {} for cid in char_ids}
                mapping = map_speakers_to_characters(transcript, mouth_motion)
                logs.append("✅ Speakers mapped to characters")

                audio_files = []
                retargeted = {}
                lip_paths = {}
                emotions = {cid: {} for cid in char_ids}
                bg_frames = {}

                for cid in char_ids:
                    script_lines = [s for s in transcript if mapping.get(s["speaker"], cid) == cid]
                    wav = generate_character_audio(
                        script_lines,
                        cid,
                        STATE["settings"]["tts_engine"],
                        list_piper_voices()[0] if STATE["settings"]["tts_engine"].startswith("Piper") and list_piper_voices() else "",
                        0,
                        1.0,
                        session_dir,
                    )
                    audio_files.append(wav)
                    logs.append(f"✅ New audio generated for Character {cid}")

                    lip = generate_lip_sync(wav, cid, fps, session_dir)
                    lip_paths[cid] = lip
                    logs.append(f"✅ Lip sync mapped for Character {cid}")

                    smoothed = smooth_character_motion(session_dir / "pose_data", cid)
                    logs.append(f"✅ Motion smoothed for Character {cid}")

                    default_char = sorted([p for p in config.CHARACTERS_DIR.iterdir() if p.is_dir()])[0]
                    retarget_path = session_dir / "character_tracks" / f"char_{cid}_retargeted.json"
                    retargeted[cid] = retarget_motion(smoothed, default_char / "config.json", retarget_path)
                    for line in script_lines:
                        start_frame = int(line["start"] * fps)
                        end_frame = int(line["end"] * fps)
                        emo = detect_emotion(line.get("text", ""))
                        for f in range(start_frame, end_frame + 1):
                            emotions[cid][f] = emo

                for idx in range(1, analysis["frames"]["total_frames"] + 1):
                    bg_name = get_background_for_scene(
                        scene_text=" ".join(t["text"] for t in transcript[:3]),
                        mode=background_mode,
                        ollama_model=STATE["settings"]["ollama_model"],
                        selected_background=single_background,
                    )
                    bg_frames[idx] = load_background(bg_name, w, h)

                char_assignments = {}
                for cid in char_ids:
                    char_assignments[cid] = sorted([p for p in config.CHARACTERS_DIR.iterdir() if p.is_dir()])[cid % max(1, len(list(config.CHARACTERS_DIR.iterdir())))]

                def cb(cur, total, frame_path):
                    q.put((cur, total, frame_path))

                render_frames(retargeted, char_assignments, lip_paths, emotions, bg_frames, (w, h), session_dir, progress_callback=cb)
                logs.append("✅ Frames rendered")
                final_video = compose_video(session_dir, fps, audio_files)
                logs.append("✅ Final video composed")

                outputs["video"] = str(final_video)
                outputs["stats"] = f"Render complete | total frames: {analysis['frames']['total_frames']} | characters: {len(char_ids)}"
                outputs["logs"] = "\n".join(logs)
            except Exception as inner:
                outputs["logs"] = f"❌ Generation failed: {inner}"

        thread = run_in_thread(worker)
        last_preview = None
        while thread.is_alive():
            try:
                cur, total, frame = q.get(timeout=0.2)
                pct = min(0.99, cur / max(1, total))
                progress(pct, desc=f"Rendering {cur}/{total}")
                last_preview = frame
            except queue.Empty:
                time.sleep(0.1)

        thread.join()
        progress(1.0, desc="Generation complete")
        return outputs["logs"], last_preview, outputs["video"], outputs["stats"]
    except Exception as exc:
        return f"❌ {exc}", None, None, ""


def open_output_folder():
    try:
        session_dir = Path(STATE["session_dir"])
        return str(session_dir)
    except Exception as exc:
        return f"Failed: {exc}"


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="AnimaForge") as demo:
        gr.Markdown("# AnimaForge 🎬")

        with gr.Tabs():
            with gr.Tab("Setup & Model Selection"):
                ollama_status = gr.Markdown("Checking Ollama...")
                ollama_model = gr.Dropdown(choices=[], label="Ollama Model")
                refresh_models = gr.Button("Refresh Ollama Models")
                whisper_model = gr.Dropdown(["tiny", "base", "small", "medium", "large"], value="base", label="Whisper")
                tts_engine = gr.Dropdown(["Piper", "CoquiTTS (XTTSv2)"], value="Piper", label="TTS Engine")
                fps = gr.Number(value=24, label="Output FPS")
                resolution = gr.Radio(["720p", "1080p", "4K"], value="1080p", label="Output Resolution")
                save_btn = gr.Button("Save Settings")
                save_status = gr.Textbox(label="Status")

            with gr.Tab("Input"):
                youtube_url = gr.Textbox(label="YouTube URL")
                local_video = gr.File(label="Or upload local video")
                analyze_btn = gr.Button("Download & Analyze Video")
                thumb = gr.Image(label="Video Thumbnail")
                duration = gr.Textbox(label="Duration")
                original_fps = gr.Textbox(label="Original FPS")
                char_count = gr.Textbox(label="Characters Detected")
                speaker_count = gr.Textbox(label="Speaker Count")
                analysis_logs = gr.Textbox(label="Analysis Log", lines=8)
                raw_transcript = gr.Textbox(label="Raw Transcript", lines=12)

            with gr.Tab("Character Assignment"):
                gr.Markdown("Dynamic character assignment is automatically managed during generation.\n"
                            "Available 2D characters are loaded from assets/characters.")
                rig_preview = gr.Image(label="Preview Character Rig")
                preview_btn = gr.Button("Preview Character Rig")

            with gr.Tab("Story & Background"):
                rewritten_script = gr.Textbox(label="Rewritten Script", lines=12)
                rewrite_btn = gr.Button("Let Ollama Rewrite Script")
                bg_mode = gr.Radio(["Auto (Ollama picks per scene)", "Single Background (you pick)", "Manual per scene"], value="Auto (Ollama picks per scene)", label="Background Mode")
                bg_choice = gr.Dropdown(choices=list_backgrounds(), label="Single Background")

            with gr.Tab("Generate"):
                generate_btn = gr.Button("🚀 Generate Animation")
                gen_logs = gr.Textbox(label="Real-time Logs", lines=12)
                frame_preview = gr.Image(label="Rendered Frame Preview")

            with gr.Tab("Output"):
                output_video = gr.Video(label="final_output.mp4")
                output_stats = gr.Textbox(label="Render Stats")
                open_folder_btn = gr.Button("Open Output Folder")
                output_folder = gr.Textbox(label="Output Folder")

        def preview_character():
            try:
                char_dirs = sorted([p for p in config.CHARACTERS_DIR.iterdir() if p.is_dir()])
                if not char_dirs:
                    return None
                candidate = char_dirs[0] / "head.png"
                if candidate.exists():
                    return str(candidate)
                pngs = list(char_dirs[0].glob("*.png"))
                return str(pngs[0]) if pngs else None
            except Exception:
                return None

        demo.load(scan_ollama_models, None, [ollama_model, ollama_status])
        refresh_models.click(scan_ollama_models, None, [ollama_model, ollama_status])
        save_btn.click(save_settings, [ollama_model, whisper_model, tts_engine, fps, resolution], [save_status])
        analyze_btn.click(download_and_analyze, [youtube_url, local_video], [thumb, duration, original_fps, char_count, speaker_count, analysis_logs, raw_transcript])
        rewrite_btn.click(rewrite_with_ollama, [raw_transcript], [rewritten_script])
        preview_btn.click(preview_character, None, [rig_preview])
        generate_btn.click(generate_animation, [rewritten_script, bg_mode, bg_choice], [gen_logs, frame_preview, output_video, output_stats])
        open_folder_btn.click(open_output_folder, None, [output_folder])

    return demo
