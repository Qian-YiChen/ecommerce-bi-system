@echo off
echo =============================================
echo   E-Commerce BI System - Full Stack Launch
echo =============================================
echo.
echo   [1/3] Starting MySQL...
echo =============================================

start "MySQL" "C:/Program Files/MySQL/MySQL Server 8.4/bin/mysqld.exe" --defaults-file="C:/Users/MSI-NB/mysql-data/my.ini" --console

timeout /t 3 /nobreak >nul
echo   MySQL started (port 3306)
echo.

echo =============================================
echo   [2/3] Starting Flask Backend...
echo =============================================

cd /d "%~dp0backend"
start "Flask Backend" D:\Anaconda\python.exe app.py

timeout /t 3 /nobreak >nul
echo   Backend started (http://127.0.0.1:5000)
echo.

echo =============================================
echo   [3/3] Starting Vue Frontend...
echo =============================================

cd /d "%~dp0frontend"
start "Vue Frontend" cmd /c "npm run dev"

echo   Frontend starting (http://localhost:5173)
echo.
echo =============================================
echo   All services launching...
echo   Frontend: http://localhost:5173
echo   Backend:  http://127.0.0.1:5000
echo   Demo:    run start_show.bat
echo =============================================
echo.
echo   Close each window to stop services.
echo =============================================
