@echo off
set PORT=5173

echo =========================================
echo  Riavvio del Server Frontend Documentale
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
echo Porta %PORT% liberata (se era occupata).
echo.
echo Avvio del server frontend con Vite...
cd frontend
npm run dev

pause
