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

REM --- start backend (minimized) ---
start "JARVIS backend" /min %PY% "%~dp0jarvis_server.py"

REM --- give it a moment ---
ping -n 3 127.0.0.1 >nul

REM --- open as an app window (Chrome, then Edge, then default browser) ---
set "CHROME="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"

set "EDGE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

if defined CHROME (
  start "" "!CHROME!" --app=%URL% --window-size=1320,860
) else if defined EDGE (
  start "" "!EDGE!" --app=%URL% --window-size=1320,860
) else (
  start "" %URL%
)

echo   JARVIS is live at %URL%
echo   ^(Close the minimized "JARVIS backend" window to shut down.^)
exit /b 0
