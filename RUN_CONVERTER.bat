@echo off
setlocal

echo.
echo  ========================================
echo   CadOwl - DXF to SiteOwl Converter
echo  ========================================
echo.

cd /d "%~dp0"

:: Check if venv exists
if not exist ".venv\Scripts\python.exe" (
    echo  [!!] Virtual environment not found!
    echo       Run SETUP.bat first.
    echo.
    pause
    exit /b 1
)

:: Run the converter
.venv\Scripts\python.exe cad2siteowl.py

echo.
echo  Opening Output folder...
if exist "Output" start "" "Output"

pause
