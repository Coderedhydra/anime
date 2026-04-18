# Text2Toon Studio (AnimaForge Rebuilt)

I rebuilt the project into a single-purpose local tool:

- You enter a story text.
- You pick an Ollama model.
- App generates a storyboard (JSON scenes).
- App renders smooth 2D rig-style multi-character animation.
- App exports `final_output.mp4` in a session folder.
- App also generates character PNGs automatically per session.

## Run

```bash
./install.sh
source .venv/bin/activate
python main.py
```

Open: http://127.0.0.1:7860

## Notes

- Everything runs locally.
- If Ollama is unavailable, a fallback storyboard generator is used.
- Session outputs are written under `workspace/session_<id>/`.
