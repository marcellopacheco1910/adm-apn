@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 py -3 -m venv .venv
 if errorlevel 1 exit /b 1
 .venv\Scripts\python.exe -m pip install -r requirements-local.txt
 if errorlevel 1 exit /b 1
)
set APN_ENV=development
start "" http://127.0.0.1:8000
.venv\Scripts\python.exe app.py --port 8000
pause
