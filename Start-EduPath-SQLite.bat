@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON=py -3"
) else (
  set "PYTHON=python"
)
%PYTHON% --version >nul 2>nul
if errorlevel 1 (
 echo Python 3 was not found. Install Python 3 from python.org.
 pause
 exit /b 1
)
echo Starting EduPath AI with the SQLite database...
start "EduPath AI SQLite Backend" cmd /k "%PYTHON% server.py"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8765"
echo Browser opened. Keep the backend terminal running.
endlocal
