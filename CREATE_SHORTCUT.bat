@echo off
:: Creates a desktop shortcut for CadOwl with custom icon
:: Run this once to set up the shortcut

set SCRIPT_DIR=%~dp0
set SHORTCUT_NAME=CadOwl
set TARGET=%SCRIPT_DIR%CadOwl.bat
set ICON=%SCRIPT_DIR%app\static\branding\cadowl.ico
set DESKTOP=%USERPROFILE%\OneDrive - Walmart Inc\Desktop
if not exist "%DESKTOP%" set DESKTOP=%USERPROFILE%\Desktop

echo Creating desktop shortcut for CadOwl...

:: Fallback icon generation for older layouts
if not exist "%ICON%" (
    set ICON=%SCRIPT_DIR%cadowl.ico
    if not exist "%ICON%" (
        if exist "%SCRIPT_DIR%create_icon.py" (
            echo Generating icon...
            python "%SCRIPT_DIR%create_icon.py"
        )
    )
)

echo Using icon: %ICON%

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\%SHORTCUT_NAME%.lnk'); $s.TargetPath = '%TARGET%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = '%ICON%,0'; $s.Description = 'CadOwl - CAD to SiteOwl Converter'; $s.WindowStyle = 7; $s.Save()"

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
