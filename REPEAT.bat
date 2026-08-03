@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0"

title Timestamps REPEAT (quality-locked)
echo.
echo ============================================================
echo   Timestamp-Pipeline wiederholen (Qualitaetsprofil)
echo ============================================================
echo.

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo [setup] Noch kein .venv — starte setup.ps1 ...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
  if errorlevel 1 goto :fail
)

if "%~1"=="" (
  echo Nutzung:
  echo   REPEAT.bat "F:\Pfad\Zum\AlbumProjekt"
  echo   REPEAT.bat "F:\Pfad\Zum\AlbumProjekt" album
  echo   REPEAT.bat "F:\Pfad\Zum\AlbumProjekt" album-hq
  echo   REPEAT.bat "F:\Pfad\Zum\AlbumProjekt" speech-de
  echo.
  echo Profile:
  "%VENV_PY%" -m crisper_timestamps.pipeline --list-profiles
  echo.
  set /p "PROJECT=Projektordner: "
  if "!PROJECT!"=="" goto :fail
  set "PROFILE=album"
) else (
  set "PROJECT=%~1"
  set "PROFILE=%~2"
  if "!PROFILE!"=="" set "PROFILE=album"
)

echo.
echo Projekt : !PROJECT!
echo Profil  : !PROFILE!
echo.
"%VENV_PY%" -m crisper_timestamps.pipeline --project "!PROJECT!" --profile "!PROFILE!"
set "RC=!errorlevel!"
echo.
if !RC! EQU 0 (
  echo Fertig. Timestamps liegen im Projekt unter "NN Timestamps" + handoff.json
) else (
  echo Fehlercode !RC!
)
pause
exit /b !RC!

:fail
echo Abbruch.
pause
exit /b 1
