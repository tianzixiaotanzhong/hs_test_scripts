@echo off
chcp 65001 >nul 2>&1
title CPU Monitor System

:MENU
cls
echo.
echo    ==========================
echo      CPU Monitor System V3
echo    ==========================
echo.
echo      [1] Stress Test
echo      [2] Temperature Monitor
echo      [3] Setup Environment
echo      [0] Exit
echo.
echo    ==========================
echo.
set /p c=Select: 

if "%c%"=="1" goto STRESS
if "%c%"=="2" goto TEMP
if "%c%"=="3" goto SETUP
if "%c%"=="0" exit
goto MENU

:STRESS
cls
echo Running stress test...
echo.
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe monitor.py stress --config config.json
) else (
    python monitor.py stress --config config.json
)
pause
goto MENU

:TEMP
cls
echo Running temperature monitor...
echo.
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe monitor.py temp --config config.json
) else (
    python monitor.py temp --config config.json
)
pause
goto MENU

:SETUP
cls
echo Setting up environment...
echo.
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
echo Installing dependencies...
.venv\Scripts\pip.exe install -q --upgrade pip
.venv\Scripts\pip.exe install -q -r requirements.txt
echo.
echo Setup complete!
pause
goto MENU