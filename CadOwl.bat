@echo off
title CadOwl
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Auto-sync to both GitHub remotes on launch
echo Syncing code to GitHub...
git add -A
git commit -m "Auto-sync on launch [%date% %time%]" 2>nul
git push origin --all 2>nul
echo Done!

pythonw cadowl_gui.py
