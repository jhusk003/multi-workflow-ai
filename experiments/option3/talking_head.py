"""Isolated local, opt-in SadTalker experiment. No imports of torch into Streamlit.

This adapter does not bundle pretrained model weights, install dependencies, or send
photos/audio to a hosted inference service. SadTalker is invoked only on button click.
"""
from __future__ import annotations

import base64
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
LAB = PROJECT / 'option3_engine'
ENGINE = LAB / 'SadTalker'
DEFAULT_PY = LAB / '.venv-sadtalker' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
CLIP_SECONDS = 10
REQUIRED_MODELS = (
    'SadTalker_V0.0.2_256.safetensors',
    'mapping_00109-model.pth.tar',
    'mapping_00229-model.pth.tar',
)


class SetupError(RuntimeError):
    pass


@dataclass
class Status:
    ready: bool
    issues: list[str]
    python: Path
    engine: Path


def check_setup(python_override: str = '', *, engine: Path | None = None, ffmpeg: str | None = None) -> Status:
    root = Path(engine) if engine else ENGINE
    interpreter = Path(python_override).expanduser() if python_override else Path(os.environ.get('SADTALKER_PYTHON') or DEFAULT_PY)
    ff = ffmpeg or shutil.which('ffmpeg')
    problems = []
    if not (root / 'inference.py').is_file():
        problems.append(f'SadTalker repository missing: {root / "inference.py"}. Run setup_option3.ps1.')
    if not interpreter.is_file():
        problems.append(f'Dedicated SadTalker Python missing: {interpreter}. Run setup_option3.ps1.')
    if not ff:
        problems.append('FFmpeg not found on PATH. Install FFmpeg, then restart PowerShell.')
    for name in REQUIRED_MODELS:
        p = root / 'checkpoints' / name
        if not p.is_file() or p.stat().st_size < 1000:
            problems.append(f'Checkpoint missing or incomplete: checkpoints/{name}. Get official model package; see README.')
    return Status(not problems, problems, interpreter, root)


def save_image(url: str, destination: Path) -> None:
    # Only the four fixed portrait URLs in ASSISTANTS are passed here.
    if not (url.startswith('https://images.unsplash.com/') or url.startswith('https://plus.unsplash.com/')):
        raise ValueError('Only configured Unsplash portrait URLs are allowed in this lab.')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 MultiWorkflowAI Option3 local lab'})
    with urllib.request.urlopen(req, timeout=25) as response:
        if not response.headers.get('Content-Type', '').lower().startswith('image/'):
            raise ValueError('Portrait URL did not return an image.')
        payload = response.read(9_000_001)
    if not payload or len(payload) > 9_000_000:
        raise ValueError('Portrait missing or exceeds 9 MB.')
    destination.write_bytes(payload)


def run_experiment(*, name: str, photo_url: str, audio_base64: str, python_override: str = '',
                   ffmpeg: str | None = None, engine: Path | None = None,
                   lab: Path | None = None, run=subprocess.run) -> Path:
    """Generate a new clip or reuse an existing one. Raises SetupError with a useful message.

    CPU-only, 256px, crop mode, max 10 sec of audio. Do not invoke on every AI reply.
    """
    status = check_setup(python_override, engine=engine, ffmpeg=ffmpeg)
    if not status.ready:
        raise SetupError('\n'.join(status.issues))
    work = Path(lab) if lab else LAB
    audio_bytes = base64.b64decode(audio_base64, validate=True)
    if len(audio_bytes) < 200:
        raise ValueError('No playable neural MP3 available. Retry neural audio in the photo panel.')
    key = hashlib.sha256(name.encode() + b'\0' + photo_url.encode() + b'\0' + audio_bytes).hexdigest()[:18]
    destination = work / 'clips' / f'{name.lower()}-{key}.mp4'
    if destination.is_file() and destination.stat().st_size > 1000:
        return destination
    job = work / 'jobs' / f'{name.lower()}-{key}'
    job.mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    mp3 = job / 'speech.mp3'
    wav = job / 'speech_10s.wav'
    image = job / 'portrait.jpg'
    mp3.write_bytes(audio_bytes)
    if not image.exists():
        save_image(photo_url, image)
    ff = ffmpeg or shutil.which('ffmpeg')
    converted = run([str(ff), '-hide_banner', '-loglevel', 'error', '-y', '-i', str(mp3),
                     '-t', str(CLIP_SECONDS), '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le',
                     str(wav)], capture_output=True, text=True, timeout=90, check=False)
    if converted.returncode != 0 or not wav.exists() or wav.stat().st_size < 500:
        raise SetupError('FFmpeg audio conversion failed: ' + (converted.stderr or '')[-1400:])
    results = job / 'results'
    results.mkdir(exist_ok=True)
    cmd = [str(status.python), 'inference.py', '--driven_audio', str(wav),
           '--source_image', str(image), '--result_dir', str(results),
           '--cpu', '--size', '256', '--batch_size', '1', '--preprocess', 'crop',
           '--expression_scale', '0.85']
    try:
        result = run(cmd, cwd=str(status.engine), capture_output=True, text=True, timeout=3600, check=False)
    except subprocess.TimeoutExpired as e:
        raise SetupError('SadTalker exceeded the one-hour CPU safety timeout. Original app is unchanged.') from e
    (job / 'run.log').write_text((result.stdout or '')[-30000:] + '\n--- STDERR ---\n' + (result.stderr or '')[-30000:], encoding='utf-8')
    videos = sorted(results.glob('*.mp4'), key=lambda p:p.stat().st_mtime, reverse=True)
    if result.returncode or not videos:
        raise SetupError('SadTalker failed (exit ' + str(result.returncode) + '). Last log lines:\n' +
                         '\n'.join((result.stderr or result.stdout or 'No output').splitlines()[-16:]) +
                         '\nFull log: ' + str(job / 'run.log'))
    shutil.copy2(videos[0], destination)
    if destination.stat().st_size < 1000:
        destination.unlink(missing_ok=True)
        raise SetupError('SadTalker returned an empty MP4. Read ' + str(job / 'run.log'))
    return destination
