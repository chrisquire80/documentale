@echo off
echo =========================================
echo  Avvio Ambiente Docker (Database + Backend)
echo =========================================
echo.

echo Verifica Docker in corso...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Docker non e' in esecuzione!
    echo Per favore, avvia Docker Desktop e riprova.
    pause
    exit /b
)

echo.
echo Avvio dei container in background...
docker-compose up -d db backend

echo.
echo I container sono stati lanciati.
echo Il backend sara' presto disponibile su http://localhost:8000
echo.
pause
