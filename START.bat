@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0"

title CrisperWhisper Timestamps
echo.
echo ============================================================
echo   CrisperWhisper — exakte Wort-Timestamps
echo ============================================================
echo.

REM --- 1) Python finden ---
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [FEHLER] Python 3.10+ nicht gefunden.
  echo          Bitte von https://www.python.org/downloads/ installieren
  echo          und "Add Python to PATH" aktivieren.
  goto :fail
)

REM --- 2) venv anlegen falls noetig ---
if not exist ".venv\Scripts\python.exe" (
  echo [setup] Erstelle virtuelle Umgebung .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [FEHLER] venv konnte nicht erstellt werden.
    goto :fail
  )
)

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "VENV_PIP=%~dp0.venv\Scripts\pip.exe"

REM --- 3) Paket installieren falls noetig ---
"%VENV_PY%" -c "import crisper_timestamps, crisperwhisper" >nul 2>&1
if errorlevel 1 (
  echo [setup] Installiere Abhaengigkeiten (einmalig, dauert ein paar Minuten)...
  "%VENV_PY%" -m pip install --upgrade pip
  if errorlevel 1 goto :fail
  "%VENV_PY%" -m pip install -e .
  if errorlevel 1 (
    echo [FEHLER] Installation fehlgeschlagen.
    goto :fail
  )
  echo [setup] Installiere PyTorch mit CUDA 12.8 (NVIDIA GPU)...
  "%VENV_PY%" -m pip install --upgrade torch --index-url https://download.pytorch.org/whl/cu128
  if errorlevel 1 (
    echo [hinweis] CUDA-Torch optional fehlgeschlagen — CPU-Fallback bleibt aktiv.
  )
  echo [setup] Installation OK.
  echo.
)

REM --- 4) ffmpeg Check (optional aber empfohlen) ---
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo [hinweis] ffmpeg nicht im PATH — WAV/FLAC funktionieren trotzdem.
  echo           Fuer MP3/M4A: https://www.gyan.dev/ffmpeg/builds/
  echo.
)

REM --- 5) Argumente oder interaktiv ---
if not "%~1"=="" (
  echo [run] Starte mit Argumenten: %*
  echo.
  "%VENV_PY%" -m crisper_timestamps %*
  set "RC=!errorlevel!"
  goto :done
)

REM Keine Args: input/ pruefen
set "INPUT_DIR=%~dp0input"
if not exist "%INPUT_DIR%" mkdir "%INPUT_DIR%"

set "COUNT=0"
for %%F in ("%INPUT_DIR%\*.wav" "%INPUT_DIR%\*.mp3" "%INPUT_DIR%\*.m4a" "%INPUT_DIR%\*.flac" "%INPUT_DIR%\*.ogg" "%INPUT_DIR%\*.opus" "%INPUT_DIR%\*.webm" "%INPUT_DIR%\*.mp4" "%INPUT_DIR%\*.mkv" "%INPUT_DIR%\*.aac" "%INPUT_DIR%\*.wma") do (
  if exist "%%~F" set /a COUNT+=1
)

if !COUNT! GTR 0 (
  echo [run] !COUNT! Datei(en) in input\ gefunden — starte Transkription...
  echo.
  "%VENV_PY%" -m crisper_timestamps "%INPUT_DIR%"
  set "RC=!errorlevel!"
  goto :done
)

echo Keine Audiodateien in input\ und keine Argumente.
echo.
echo   Option A: Audio-Datei(en) in den Ordner  input\  legen,
echo             dann dieses Fenster schliessen und START.bat erneut starten.
echo.
echo   Option B: Pfad jetzt eingeben (Datei oder Ordner):
set /p "USERPATH=Pfad: "
if "!USERPATH!"=="" (
  echo Abgebrochen.
  set "RC=2"
  goto :done
)
echo.
"%VENV_PY%" -m crisper_timestamps "!USERPATH!"
set "RC=!errorlevel!"

:done
echo.
if not defined RC set "RC=0"
if !RC! EQU 0 (
  echo Fertig. Ergebnisse liegen in: output\
) else (
  echo Beendet mit Fehlercode !RC!.
)
echo.
pause
exit /b !RC!

:fail
echo.
pause
exit /b 1
