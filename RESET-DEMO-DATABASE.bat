@echo off
cd /d "%~dp0"
echo WARNING: Resets all local demonstration records to their original fictional state.
choice /C YN /M "Reset database"
if errorlevel 2 exit /b 0
where py >nul 2>nul
if not errorlevel 1 (py -3 server.py --reset) else (python server.py --reset)
pause
