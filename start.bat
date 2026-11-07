@echo off
REM Paytience: double-click to start (Windows). First run installs everything.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 start.py) else (python start.py)
pause
