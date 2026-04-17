# AnimaForge v1.0 🎬

AnimaForge is a local-first Gradio tool that transforms an input video (YouTube URL or local file) into a newly rendered 2D cartoon while preserving story timing and motion structure.

## Features
- End-to-end local pipeline (yt-dlp, ffmpeg, Whisper, Ollama, Piper/Coqui).
- Multi-character detection + tracking.
- Pose extraction and smoothing.
- Retargeted 2D rig rendering without diffusion models.
- Story rewriting, emotion tagging, lip sync mapping.
- Final MP4 composition in one run.

## Project layout
```
main.py
ui.py
config.py
core/
assets/
models/
workspace/
```

## Quick start
### Linux / macOS
```bash
./install.sh
source .venv/bin/activate
python main.py
```

### Windows
```bat
install.bat
.venv\Scripts\activate
python main.py
```

Open: `http://localhost:7860`

## Notes
- Ensure `ollama serve` is running and at least one model is pulled.
- Add/replace character rigs in `assets/characters/*`.
- Put Piper voices into `models/piper/`.

## Output
Each run creates a UUID-isolated session under `workspace/session_<id>/` with:
- raw input video
- extracted frames/audio
- character tracks and pose JSON
- generated TTS, lip-sync maps, rendered frames
- `final_output.mp4`


## Asset generation
- Placeholder PNG assets are generated locally by `generate_assets.py` and are not committed as binaries.
- Run `python generate_assets.py` anytime to regenerate `assets/backgrounds/*.png` and character part PNGs.
