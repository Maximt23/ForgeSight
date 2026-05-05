@echo off
echo.
echo  ========================================
echo   🦉 CadOwl - DXF to SiteOwl Converter
echo  ========================================
echo.

cd /d "%~dp0"

echo  Running Python converter...
echo.

.venv\Scripts\python.exe cad2siteowl.py

echo.
echo  Opening Output folder...
start "" "%~dp0..\Output"

pause
