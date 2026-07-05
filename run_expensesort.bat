@echo off
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
echo Starting ExpenseSort... a browser tab will open at http://localhost:8001
start "" http://localhost:8001
"%PY%" app.py
echo.
echo ExpenseSort stopped. Press any key to close.
pause >nul
