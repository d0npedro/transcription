#Requires -Version 5.1
<#
.SYNOPSIS
  Wrapper um die CLI (nutzt .venv falls vorhanden).
.EXAMPLE
  .\transcribe.ps1 input\meeting.wav
  .\transcribe.ps1 input -Language en -Model medium
#>
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-Location $PSScriptRoot
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "Kein .venv — starte setup.ps1 ..." -ForegroundColor Yellow
    & "$PSScriptRoot\setup.ps1"
}
& $venvPy -m crisper_timestamps @CliArgs
exit $LASTEXITCODE
