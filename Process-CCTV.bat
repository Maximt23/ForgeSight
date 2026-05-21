@echo off
title CadOwl - CCTV Pipeline
color 0B
cd /d "%~dp0"

echo ========================================
echo   CadOwl - CCTV
echo   Flow: Input (DWG) - Staging (DXF) - Output (CSV)
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Use system-aware processing (auto-detects folders)
python cad2siteowl_enhanced.py --system cctv

echo.
echo ========================================
echo   CCTV Processing Complete!
echo ========================================
pause
