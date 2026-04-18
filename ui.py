from pathlib import Path
import json

import gradio as gr

from animator import render_animation
from config import DEFAULTS, RESOLUTIONS
from story_brain import generate_storyboard_with_ollama, list_ollama_models


def build_app():
    with gr.Blocks(title="Text2Toon Studio") as app:
        gr.Markdown("# Text2Toon Studio 🎬\nEnter a story, choose an Ollama model, and generate a 2D animation video.")

        with gr.Row():
            model = gr.Dropdown(label="Ollama Model", choices=list_ollama_models(), allow_custom_value=True)
            refresh = gr.Button("Refresh Models")

        story = gr.Textbox(label="Story Prompt", lines=8, placeholder="A fox and three friends build a flying bike...")
        with gr.Row():
            duration = gr.Slider(5, 60, value=DEFAULTS["duration"], step=1, label="Duration (sec)")
            fps = gr.Slider(12, 30, value=DEFAULTS["fps"], step=1, label="FPS")
            resolution = gr.Dropdown(list(RESOLUTIONS.keys()), value=DEFAULTS["resolution"], label="Resolution")
            char_count = gr.Slider(1, 8, value=DEFAULTS["character_count"], step=1, label="Characters")

        storyboard_preview = gr.Code(label="Storyboard JSON", language="json")
        generate_storyboard_btn = gr.Button("Generate Storyboard")

        generate_btn = gr.Button("🚀 Generate Animation")
        logs = gr.Textbox(label="Logs", lines=10)
        out_video = gr.Video(label="Result Video")
        out_session = gr.Textbox(label="Session Folder")
        out_char_dir = gr.Textbox(label="Generated Character PNG Folder")

        def refresh_models():
            try:
                models = list_ollama_models()
                return gr.update(choices=models)
            except Exception:
                return gr.update(choices=[])

        def build_storyboard(story_text, model_name, dur, ccount):
            try:
                board = generate_storyboard_with_ollama(story_text, model_name, int(dur), int(ccount))
                return json.dumps(board, indent=2), "Storyboard generated ✅"
            except Exception as exc:
                return "[]", f"Storyboard failed: {exc}"

        def generate(story_text, model_name, dur, fps_v, res_key, ccount, board_text, progress=gr.Progress()):
            try:
                progress(0.0, desc="Preparing")
                if board_text and board_text.strip() and board_text.strip().startswith("["):
                    board = json.loads(board_text)
                else:
                    board = generate_storyboard_with_ollama(story_text, model_name, int(dur), int(ccount))

                def cb(ratio, msg):
                    progress(min(1.0, max(0.0, ratio)), desc=msg)

                result = render_animation(
                    story=story_text,
                    storyboard=board,
                    duration=int(dur),
                    fps=int(fps_v),
                    resolution=RESOLUTIONS[res_key],
                    progress_fn=cb,
                )
                return "Animation generated ✅", result["video_path"], result["session_dir"], result["characters_dir"]
            except Exception as exc:
                return f"Generation failed: {exc}", None, "", ""

        refresh.click(refresh_models, outputs=[model])
        generate_storyboard_btn.click(build_storyboard, [story, model, duration, char_count], [storyboard_preview, logs])
        generate_btn.click(generate, [story, model, duration, fps, resolution, char_count, storyboard_preview], [logs, out_video, out_session, out_char_dir])

    return app
