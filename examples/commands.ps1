#Requires -Version 5.1
# Copy-paste recipes for crisper-timestamps (run from repo root after setup.ps1).
# Usage:
#   . .\examples\commands.ps1
#   Invoke-ExampleListProfiles
#   Invoke-ExampleSingleFile -Audio "D:\takes\clip.wav"
#   Invoke-ExampleAlbum -Project "F:\Albums\My Album"

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot ".venv\Scripts\python.exe"))) {
    Write-Warning "No .venv — run .\setup.ps1 first from repo root."
}
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"

function Invoke-ExampleListProfiles {
    & $Py -m crisper_timestamps.pipeline --list-profiles
}

function Invoke-ExampleSingleFile {
    param(
        [Parameter(Mandatory = $true)][string]$Audio,
        [string]$Language = "de",
        [ValidateSet("verbatim", "intended")][string]$Mode = "verbatim",
        [string]$OutDir = (Join-Path $RepoRoot "output\example-single")
    )
    & $Py -m crisper_timestamps $Audio -l $Language --mode $Mode -m turbo -o $OutDir
}

function Invoke-ExampleAlbum {
    param(
        [Parameter(Mandatory = $true)][string]$Project,
        [ValidateSet("album", "album-hq", "speech-de", "speech-en")][string]$Profile = "album",
        [string]$Language
    )
    $args = @("-m", "crisper_timestamps.pipeline", "--project", $Project, "--profile", $Profile)
    if ($Language) { $args += @("--language", $Language) }
    & $Py @args
}

function Invoke-ExampleHandoffRebuild {
    param(
        [Parameter(Mandatory = $true)][string]$OutputDir,
        [string]$Id = "example",
        [string]$Language = "en",
        [string]$Mode = "intended",
        [string]$Model = "turbo"
    )
    & $Py -m crisper_timestamps.handoff $OutputDir --id $Id --language $Language --mode $Mode --model $Model
}

function Invoke-ExampleConsumeHandoff {
    param([Parameter(Mandatory = $true)][string]$HandoffJson)
    & $Py (Join-Path $PSScriptRoot "03-handoff-consumer\consume_handoff.py") $HandoffJson
}
