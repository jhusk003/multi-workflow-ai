# Multi-Workflow AI — Option 3 Talking-Head Experiment

**Your baseline is protected.** `app.py` is the byte-for-byte Version 6.1 photo app. `app_option3.py` is an experimental copy with ONE added expander for short AI talking-head MP4 generation. It preserves all four independent workspaces, voices, histories, file uploads and tasks. No models or model weights are bundled; nothing has been deployed to Render.

## What you get

- `app.py`: unmodified original Version 6.1.
- `app_option3.py`: same app plus optional **Option 3 video experiment** expander.
- `talking_head.py`: CPU-only SadTalker inference adapter, FFmpeg MP3-to-WAV preparation, error logs and MP4 caching.
- `setup_option3.ps1`: isolated SadTalker Python 3.8 installation. **Does not touch the main .venv or app.py.**
- `baseline_v6_1/`: another protected copy of the original source and deployment requirements.
- `option3_engine/`: generated only after setup; excluded from Git because it includes model weights and private voice/video outputs.

## Installation on Windows

Save this ZIP, unzip into a NEW folder, preferably `C:\Users\jasmi\Desktop\multi-workflow-ai-option3` (do NOT extract over the running `multi-workflow-ai`). To retain your current local API keys and config, copy your personal `.streamlit/secrets.toml` into the experiment directory's `.streamlit/` folder yourself; never commit it. Or use environment variables for GROQ_API_KEY, GEMINI_API_KEY, and OLLAMA_HOST. The original app's AI provider fallback will also work if Ollama is running at localhost:11434.

1. Open PowerShell in the **new** extracted folder. `py -3.8 --version`, `git --version`, and `ffmpeg -version` must work. If Python 3.8 is missing, install it separately (official SadTalker setup is legacy; do not change your working Python). If FFmpeg is missing, `winget install --id Gyan.FFmpeg -e` can install it; restart PowerShell after installation. [Official SadTalker](https://github.com/OpenTalker/SadTalker).
2. Run `Set-ExecutionPolicy -Scope Process Bypass -Force`, then `.\setup_option3.ps1` (installs a separate CPU-only environment; substantial downloads and free disk space required). If legacy dependencies fail, stop and preserve the error output instead of installing them into your main app.
3. Download the **official** SadTalker model bundle from [SadTalker Releases](https://github.com/OpenTalker/SadTalker/releases), extract required checkpoints into `option3_engine\SadTalker\checkpoints\`, following the official model download instructions. For the 256px new model, ensure `SadTalker_V0.0.2_256.safetensors`, `mapping_00109-model.pth.tar`, `mapping_00229-model.pth.tar` exist. The official package may also contain support files or directories needed for preprocessing. Do not commit the model files. GPU enhancer is deliberately disabled.
4. Install the same lightweight UI dependencies into your MAIN application Python environment if not already installed: `python -m pip install -r requirements.txt`. Run `python -m streamlit run app_option3.py --server.port 8502` in the experiment folder. This uses the **main** Streamlit Python; the separate SadTalker Python is called only when generating video.
5. Select Alex, click the **Option 3 video experiment** expander, and click Generate to make a brief MP4. Check blinking and expressions. Repeat with the other assistants. The video plays with the baked-in neural voice; don't also click the original portrait's Speak response at the same time.

**CPU reality:** Video generation can be slow and use substantial RAM/disk; it is on demand, never on each chat turn. The first test is a short voice sample. Maximum processed speech is 10 seconds. Model installation and successful video inference **must be tested on your PC**; packaging/syntax checks alone do not establish that the full model runs. Do not attempt to deploy the local CPU model on Render Free. Existing photo avatar stays available.

**Photo and privacy:** The current app's portrait URLs point to Unsplash photos of real people. For public-facing demos use images you have permission to animate, or your own synthetic portraits. Image and speech are processed locally by SadTalker, apart from the existing Edge TTS audio service and the existing Unsplash image download.

## To abandon

Simply stop the experimental app (`Ctrl+C`) and restart your original `multi-workflow-ai` project with `python -m streamlit run app.py --server.port 8501`. The original folder was never modified. If operating solely within this ZIP, `baseline_v6_1\app.py` is an exact copy of the original working Version 6.1 source. Say **abandon** in chat and we will build Option 1 from the working baseline instead. You can delete the experiment folder at any time.
