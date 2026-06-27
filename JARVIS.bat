@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PORT=8765"
set "URL=http://127.0.0.1:%PORT%/"

echo.
echo   Booting J.A.R.V.I.S. ...
echo.

REM --- locate python ---
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py" )
if not defined PY (
  echo   [!] Python not found on PATH. Install Python 3 and try again.
  pause & exit /b 1
)

REM --- optional: real telemetry ---
%PY% -c "import psutil" 2>nul || (
  echo   Installing psutil for real CPU/RAM telemetry ^(optional^)...
  %PY% -m pip install --quiet psutil 2>nul
)

REM --- start backend minimized; it opens the HUD app window itself (--open) ---
REM    The window-detection logic lives in jarvis_server.py so every platform
REM    (Windows .bat, macOS/Linux jarvis.sh) shares one implementation.
start "JARVIS backend" /min %PY% "%~dp0jarvis_server.py" --open

echo   JARVIS is live at %URL%
echo   ^(Close the minimized "JARVIS backend" window to shut down.^)
exit /b 0
