#Requires -Version 5.1
<#
.SYNOPSIS
  Wiederholbarer Timestamp-Lauf mit Qualitätsprofil (Album / Speech).

.EXAMPLE
  .\repeat.ps1 -Project "F:\Downloads\Noch ein Bier bis zum Mond"
  .\repeat.ps1 -Project "F:\Albums\X" -Profile album-hq -Language en
  .\repeat.ps1 -ListProfiles
#>
param(
    [string]$Project,
    [string]$AudioDir,
    [string]$Profile = "album",
    [string]$Language,
    [string]$Model,
    [ValidateSet("verbatim", "intended", $null)]
    [string]$Mode,
    [string]$HandoffId,
    [string]$DeployPath,
    [switch]$NoDeploy,
    [switch]$ListProfiles,
    [switch]$Recursive
)

Set-Location $PSScriptRoot
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "Kein .venv — setup.ps1 ..." -ForegroundColor Yellow
    & "$PSScriptRoot\setup.ps1"
}

$argsList = @("-m", "crisper_timestamps.pipeline")

if ($ListProfiles) {
    & $venvPy @argsList --list-profiles
    exit $LASTEXITCODE
}

if ($Project) { $argsList += @("--project", $Project) }
if ($AudioDir) { $argsList += @("--audio-dir", $AudioDir) }
if ($Profile) { $argsList += @("--profile", $Profile) }
if ($Language) { $argsList += @("--language", $Language) }
if ($Model) { $argsList += @("--model", $Model) }
if ($Mode) { $argsList += @("--mode", $Mode) }
if ($HandoffId) { $argsList += @("--handoff-id", $HandoffId) }
if ($DeployPath) { $argsList += @("--deploy-path", $DeployPath) }
if ($NoDeploy) { $argsList += @("--deploy", "none") }
if ($Recursive) { $argsList += @("--recursive") }

if (-not $Project -and -not $AudioDir) {
    Write-Host "Bitte -Project oder -AudioDir angeben. Beispiele:" -ForegroundColor Yellow
    Write-Host '  .\repeat.ps1 -Project "F:\Downloads\Noch ein Bier bis zum Mond"'
    Write-Host '  .\repeat.ps1 -ListProfiles'
    exit 2
}

& $venvPy @argsList
exit $LASTEXITCODE
