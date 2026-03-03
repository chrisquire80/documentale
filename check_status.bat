@echo off
echo --- DIAGNOSTIC REPORT ---
echo.
echo [1] Docker Service Status
powershell -Command "Get-Service -Name 'com.docker.service' | Select-Object Status, StartType, DisplayName"
echo.
echo [2] WSL Status
wsl -l -v
echo.
echo [3] Docker Process Check
tasklist | findstr /I "docker"
echo.
echo [4] Node/Vite Process Check
tasklist | findstr /I "node"
echo.
echo --- END OF REPORT ---
pause
