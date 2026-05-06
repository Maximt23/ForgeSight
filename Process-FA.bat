@echo off
title CadOwl - Fire Alarm / Intrusion Pipeline
color 0C
cd /d "%~dp0"

echo ========================================
echo   CadOwl - Fire Alarm / Intrusion
echo   System: FA
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

set INPUT_FA=C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\Input-FA
set OUTPUT_FA=C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\Output-Fire

echo Input:  %INPUT_FA%
echo Output: %OUTPUT_FA%
echo.

python cad2siteowl_enhanced.py --input "%INPUT_FA%" --output "%OUTPUT_FA%" --system fa

echo.
echo ========================================
echo   FA Processing Complete!
echo ========================================
pause
