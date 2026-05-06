@echo off
title CadOwl - Dual Pipeline Launcher
color 0E
cd /d "%~dp0"

echo ========================================
echo   CadOwl - Dual Pipeline Processor
echo   Launching FA + CCTV simultaneously
echo ========================================
echo.

REM Auto-sync to GitHub on launch
echo Syncing code to GitHub...
git add -A
git commit -m "Auto-sync on launch [%date% %time%]" 2>nul
git push origin --all 2>nul
echo.

echo Starting Fire Alarm / Intrusion pipeline...
start "CadOwl-FA" cmd /c "Process-FA.bat"

echo Starting CCTV pipeline...
start "CadOwl-CCTV" cmd /c "Process-CCTV.bat"

echo.
echo Both pipelines launched in separate windows!
echo.
echo ========================================
echo   Monitor the terminals for progress
echo ========================================
echo.
pause
