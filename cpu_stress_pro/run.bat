@echo off
chcp 65001 >nul 2>&1
title CPU压力测试系统

echo.
echo    ==============================
echo      CPU压力测试系统
echo    ==============================
echo.

if exist ".venv\Scripts\python.exe" (
    echo 使用虚拟环境运行...
    .venv\Scripts\python.exe -u monitor.py
) else (
    echo 使用系统Python运行...
    python -u monitor.py
)

echo.
echo 程序结束，按任意键退出...
pause >nul