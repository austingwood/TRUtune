@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 (
    echo.
    echo TRUtune setup failed. Read the error above.
    pause
    exit /b 1
)
echo.
echo TRUtune setup completed.
pause
