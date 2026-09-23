@echo off
chcp 65001 >nul
where python >nul 2>nul
if errorlevel 1 (
    echo Python not found. Install it from python.org
    pause
    exit /b 1
)
python main.py
pause