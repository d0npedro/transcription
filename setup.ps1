#Requires -Version 5.1
<#
.SYNOPSIS
  Einmal-Setup: venv + CrisperWhisper-Timestamps installieren.
.EXAMPLE
  .\setup.ps1
  .\setup.ps1 -ModelPrefetch turbo
#>
param(
    [ValidateSet("none", "small", "turbo", "medium", "large")]
    [string]$ModelPrefetch = "none",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Find-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    throw "Python 3.10+ nicht gefunden. Bitte von https://www.python.org/downloads/ installieren."
}

$py = Find-Python
Write-Host "==> Python: $($py -join ' ')" -ForegroundColor Cyan

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if ($Force -or -not (Test-Path $venvPy)) {
    Write-Host "==> Erstelle .venv ..." -ForegroundColor Cyan
    & @py -m venv .venv
}

$venvPy = (Resolve-Path $venvPy).Path
Write-Host "==> pip upgrade + install -e ." -ForegroundColor Cyan
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -e .

# Windows default pip torch is CPU-only — pull CUDA 12.8 wheels for NVIDIA GPUs
Write-Host "==> PyTorch CUDA 12.8 (falls NVIDIA-GPU vorhanden) ..." -ForegroundColor Cyan
try {
    & $venvPy -m pip install --upgrade torch --index-url https://download.pytorch.org/whl/cu128
} catch {
    Write-Host "  CUDA-Torch optional fehlgeschlagen — CPU-Fallback bleibt aktiv." -ForegroundColor Yellow
}

# Ordner
New-Item -ItemType Directory -Force -Path "input", "output" | Out-Null

Write-Host "==> Sanity-Import" -ForegroundColor Cyan
& $venvPy -c "from crisper_timestamps import __version__; import crisperwhisper; print('crisper-timestamps', __version__, '| crisperwhisper OK')"

if ($ModelPrefetch -ne "none") {
    Write-Host "==> Prefetch Modell '$ModelPrefetch' (Download von HuggingFace) ..." -ForegroundColor Cyan
    & $venvPy -c @"
from crisperwhisper import CrisperWhisperModel
print('loading $ModelPrefetch ...')
m = CrisperWhisperModel('$ModelPrefetch', backend='transformers', device='auto')
print('backend=', getattr(m, 'backend', '?'))
print('prefetch OK')
"@
}

Write-Host ""
Write-Host "Setup fertig." -ForegroundColor Green
Write-Host "  1) Audio in .\input\ legen"
Write-Host "  2) START.bat doppelklicken  ODER:"
Write-Host "     .\.venv\Scripts\python.exe -m crisper_timestamps"
Write-Host ""
