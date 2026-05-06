@echo off
title CadOwl - Dual Watcher Mode
color 0A
cd /d "%~dp0"

echo ========================================
echo   CadOwl - Dual File Watcher Mode
echo   Watches FA + CCTV folders for new DWG
echo ========================================
echo.

REM Auto-sync to GitHub on launch
echo Syncing code to GitHub...
git add -A
git commit -m "Auto-sync on launch [%date% %time%]" 2>nul
git push origin --all 2>nul
echo.

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo Starting FA watcher...
start "CadOwl-Watcher-FA" cmd /k "python watcher.py --system fa"

timeout /t 2 >nul

echo Starting CCTV watcher...
start "CadOwl-Watcher-CCTV" cmd /k "python watcher.py --system cctv"

echo.
echo ========================================
echo   Both watchers running!
echo   Drop DWG files into Input folders:
echo.
echo   FA:   Input-FA
echo   CCTV: Input-CCTV
echo ========================================
echo.
pause
