@echo off
rem ============================================================================
rem  Auto VRAM Optimizer -- VRAM auto-config launcher
rem  "The Man, The Mythos, The Legend : KeilerHirsch"   (GPLv3)
rem
rem  Double-click this once. It detects your graphics-card memory (NVIDIA / AMD
rem  / Intel) and writes the mod's settings file, so FS25's texture budget
rem  matches your card automatically -- no editing. Run it again if you change
rem  graphics cards.
rem ============================================================================
setlocal
set "PYTHONUTF8=1"
title Auto VRAM Optimizer - Auto VRAM

set "HERE=%~dp0"
set "SCRIPT=%HERE%configure_vram.py"

if not exist "%SCRIPT%" (
  echo   [X] configure_vram.py is missing next to this launcher.
  echo       Keep the whole Auto VRAM Optimizer tool folder together.
  echo(
  pause
  exit /b 1
)

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo   [X] Python 3 was not found on this PC.
  echo       Install it from  https://www.python.org/downloads/
  echo       and tick "Add python.exe to PATH" during setup, then try again.
  echo(
  pause
  exit /b 1
)

rem Switch to UTF-8 only around the Python run, then restore the previous
rem codepage. chcp changes CONSOLE state that endlocal does NOT revert, so
rem without this, running the launcher from an existing terminal would leave
rem that terminal stuck on codepage 65001. The early exits above stay on the
rem original codepage (their messages are ASCII), so they need no restore.
set "AVO_CP="
for /f "tokens=2 delims=:" %%C in ('chcp') do set "AVO_CP=%%C"
rem chcp output is localized and some locales append punctuation to the number
rem (German prints "Aktive Codepage: 850." with a trailing dot), so keep only the
rem leading numeric field, stripping both spaces and a trailing period.
for /f "tokens=1 delims=. " %%N in ("%AVO_CP%") do set "AVO_CP=%%N"
chcp 65001 >nul
%PY% "%SCRIPT%"
if defined AVO_CP chcp %AVO_CP% >nul

echo(
pause
endlocal
