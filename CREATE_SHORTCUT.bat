@echo off
:: Creates a desktop shortcut for CadOwl
:: Run this once to set up the shortcut

set SCRIPT_DIR=%~dp0
set SHORTCUT_NAME=CadOwl
set TARGET=%SCRIPT_DIR%CadOwl.bat
set DESKTOP=%USERPROFILE%\Desktop

echo Creating desktop shortcut for CadOwl...

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\%SHORTCUT_NAME%.lnk'); $s.TargetPath = '%TARGET%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Description = 'CadOwl - CAD to SiteOwl Converter'; $s.WindowStyle = 7; $s.Save()"

if exist "%DESKTOP%\%SHORTCUT_NAME%.lnk" (
    echo.
    echo ========================================
    echo   Shortcut created on your Desktop!
    echo   Look for "CadOwl" icon
    echo ========================================
) else (
    echo.
    echo ERROR: Failed to create shortcut
)

pause
