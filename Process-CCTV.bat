@echo off
title CadOwl - CCTV Pipeline
color 0B
cd /d "%~dp0"

echo ========================================
echo   CadOwl - CCTV
echo   System: CCTV
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

set INPUT_CCTV=C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\Input-CCTV
set OUTPUT_CCTV=C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\Output-CCTV

echo Input:  %INPUT_CCTV%
echo Output: %OUTPUT_CCTV%
echo.

python cad2siteowl_enhanced.py --input "%INPUT_CCTV%" --output "%OUTPUT_CCTV%" --system cctv

echo.
echo ========================================
echo   CCTV Processing Complete!
echo ========================================
pause
