@echo off
setlocal

echo.
echo  ========================================
echo   CadOwl - Setup
echo  ========================================
echo.

cd /d "%~dp0"

:: Create folders if they don't exist
if not exist "Input" mkdir Input
if not exist "Output" mkdir Output

echo  [OK] Created Input/ and Output/ folders
echo.

:: Check for Python/uv
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [!!] uv not found. Please install uv first:
    echo       https://docs.astral.sh/uv/getting-started/installation/
    echo.
    pause
    exit /b 1
)

echo  [OK] uv found
echo.

:: Create virtual environment
if not exist ".venv" (
    echo  Creating Python virtual environment...
    uv venv
    echo  [OK] Virtual environment created
) else (
    echo  [OK] Virtual environment exists
)
echo.

:: Install dependencies
echo  Installing Python dependencies...
uv pip install ezdxf
echo  [OK] Dependencies installed
echo.

echo  ========================================
echo   SETUP COMPLETE!
echo  ========================================
echo.
echo  NEXT STEPS:
echo.
echo   1. Put DWG files in the Input\ folder
echo.
echo   2. Open AutoCAD and run:
echo      (load "%~dp0DWG2DXF.lsp")
echo      DWG2DXFBATCH
echo.
echo   3. Double-click RUN_CONVERTER.bat
echo.
echo   4. CSV files appear in Output\ folder!
echo.
echo  ========================================
echo.

pause
