@echo off
echo =========================================
echo  Avvio Completo Progetto Documentale
echo =========================================
echo.

echo [1/3] Pulizia porte (REST e Vite)...
for %%P in (5173) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%%P"') do (
        if not "%%a"=="0" (
            taskkill /F /PID %%a 2>nul
        )
    )
)

echo.
echo [2/3] Avvio Backend e Database (Docker)...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ATTENZIONE] Docker non sembra in esecuzione.
    echo Assicurati che Docker Desktop sia avviato sul tuo PC per eseguire il database e il server!
    echo Premi un tasto per lanciare COMUNQUE il frontend...
    pause >nul
) else (
    docker-compose up -d db backend
)

echo.
echo [3/3] Avvio Frontend (Vite)...
cd frontend
start "Documentale Frontend" cmd /k "npm run dev"

echo.
echo Fatto! Il server Vite frontend e' in esecuzione in una nuova finestra.
echo Potrai accedere all'app all'indirizzo http://localhost:5173
echo.
pause
