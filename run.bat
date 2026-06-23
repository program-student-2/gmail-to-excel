@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Shukatsu Mail to Excel - Setup ^& Run
echo ============================================

REM --- 仮想環境（初回のみ作成） ---
if not exist ".venv\Scripts\python.exe" (
    echo [Setup] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [Error] Python not found. Install Python 3.10+ first.
        pause
        exit /b 1
    )
    echo [Setup] Installing packages...
    ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
    ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
)

REM --- 実行 ---
".venv\Scripts\python.exe" main.py

echo.
pause
