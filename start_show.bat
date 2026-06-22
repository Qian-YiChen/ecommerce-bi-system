@echo off
echo =============================================
echo   E-Commerce BI System - Demo Show
echo =============================================
echo.
echo   Starting local server on port 8000...
echo   Opening demo page in browser...
echo   Press Ctrl+C to stop
echo =============================================
echo.

cd /d "%~dp0"

start "" D:\Anaconda\python.exe -m http.server 8000

timeout /t 2 /nobreak >nul

start http://127.0.0.1:8000/demo/
