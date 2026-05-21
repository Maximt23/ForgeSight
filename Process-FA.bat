@echo off
title CadOwl - Fire Alarm / Intrusion Pipeline
color 0C
cd /d "%~dp0"

echo ========================================
echo   CadOwl - Fire Alarm / Intrusion
echo   Flow: Input (DWG) - Staging (DXF) - Output (CSV)
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Use system-aware processing (auto-detects folders)
python cad2siteowl_enhanced.py --system fa

echo.
echo ========================================
echo   FA Processing Complete!
echo ========================================
pause
