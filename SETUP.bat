@echo off
echo.
echo  ========================================
echo   🦉 CadOwl Setup
echo  ========================================
echo.

:: Set the base folder (where this script is located)
set "BASE=%~dp0"

:: Create Input and Output folders
echo  Creating folders...
if not exist "%BASE%Input" mkdir "%BASE%Input"
if not exist "%BASE%Output" mkdir "%BASE%Output"

echo   ✅ Input\  - Drop your DWG files here
echo   ✅ Output\ - CSVs will appear here
echo.

:: Check if AutoCAD is likely installed
where /q acad.exe 2>nul
if %ERRORLEVEL%==0 (
    echo  ✅ AutoCAD detected
) else (
    echo  ⚠️  AutoCAD not in PATH - that's OK, just open it manually
)

echo.
echo  ========================================
echo   SETUP COMPLETE!
echo  ========================================
echo.
echo  NEXT STEPS:
echo.
echo   1. Open AutoCAD
echo.
echo   2. Paste this in the command line:
echo      (load "%BASE:\=/%CAD2SITEOWL_AUTO.lsp")
echo.
echo   3. Drop DWG files in the Input folder
echo.
echo   4. Type: CAD2SOBATCH
echo.
echo   5. CSVs appear in Output folder!
echo.
echo  ========================================
echo.
pause
