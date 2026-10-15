# Opt-in local CPU engine installation; cannot overwrite original app.py.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$engineHome = Join-Path $PSScriptRoot 'option3_engine'
$repo = Join-Path $engineHome 'SadTalker'
$python = Join-Path $engineHome '.venv-sadtalker\Scripts\python.exe'
Write-Host 'OPTION 3 — Isolated SadTalker CPU setup (your existing app.py is untouched)' -ForegroundColor Cyan
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is missing. Install Git for Windows, then reopen PowerShell.' }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw 'FFmpeg is missing. Install FFmpeg, restart PowerShell, and rerun. Try: winget install --id Gyan.FFmpeg -e' }
& py -3.8 --version
if ($LASTEXITCODE -ne 0) { throw 'Python 3.8 is required by the original SadTalker setup. Install a standalone Python 3.8 and rerun. Do not replace the main app Python.' }
New-Item -ItemType Directory -Force -Path $engineHome | Out-Null
if (-not (Test-Path (Join-Path $repo 'inference.py'))) {
    if (Test-Path $repo) { throw 'SadTalker folder exists but inference.py is missing. Repair that folder manually.' }
    git clone https://github.com/OpenTalker/SadTalker.git $repo
    if ($LASTEXITCODE -ne 0) { throw 'Git clone failed.' }
}
if (-not (Test-Path $python)) {
    py -3.8 -m venv (Join-Path $engineHome '.venv-sadtalker')
    if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
}
& $python -m pip install --upgrade 'pip<25' 'setuptools<70' wheel
if ($LASTEXITCODE -ne 0) { throw 'pip bootstrap failed.' }
# Separate old CPU-only PyTorch. Never install these in the main Streamlit .venv.
& $python -m pip install 'torch==1.12.1+cpu' 'torchvision==0.13.1+cpu' 'torchaudio==0.12.1' --extra-index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw 'CPU PyTorch installation failed; inspect the output.' }
& $python -m pip install -r (Join-Path $repo 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'SadTalker requirements failed; inspect the output. Existing app remains untouched.' }
Write-Host ''
Write-Host 'Engine Python and dependencies set up.' -ForegroundColor Green
Write-Host 'NEXT: download official SadTalker model package from https://github.com/OpenTalker/SadTalker/releases'
Write-Host ('Extract checkpoint files into: ' + (Join-Path $repo 'checkpoints'))
Write-Host 'Required for 256px: SadTalker_V0.0.2_256.safetensors, mapping_00109-model.pth.tar, mapping_00229-model.pth.tar.'
Write-Host 'Also follow the official checkpoint instructions for any support/model directories.'
Write-Host 'After placing checkpoints, run: python -m streamlit run app_option3.py --server.port 8502'
