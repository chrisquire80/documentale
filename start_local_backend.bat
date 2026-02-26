@echo off
set PORT=8000

echo =========================================
echo  Avvio del Server Backend Locale (FastAPI)
echo =========================================
echo.

echo Cerco i processi in esecuzione sulla porta %PORT%...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT%"') do (
    if not "%%a"=="0" (
        echo Terminazione del processo con PID %%a...
        taskkill /F /PID %%a 2>nul
    )
)

echo.
echo Avvio del server backend FastAPI con Uvicorn...
cd backend
echo Ricorda che devi avere un .env corretto in questa cartella.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
