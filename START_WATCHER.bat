@echo off
setlocal

echo.
echo  ========================================
echo   CadOwl File Watcher
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

:: Run the watcher
.venv\Scripts\python.exe watcher.py

pause
