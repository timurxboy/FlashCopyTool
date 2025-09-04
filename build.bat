@echo off
chcp 65001 >nul
echo [=== Сборка FlashCopyTool ===]

:: Путь к виртуальному окружению
set VENV_PATH=%~dp0venv

:: Активируем venv
call "%VENV_PATH%\Scripts\activate.bat"

:: Собираем exe
pyinstaller --onefile --windowed --name FlashCopyTool ^
    --hidden-import win32timezone ^
    --hidden-import boto3 ^
    --hidden-import botocore ^
    --hidden-import sqlite3 ^
    --hidden-import logging.handlers ^
    --hidden-import win32gui ^
    --hidden-import win32con ^
    main.py

echo [=== Сборка завершена ===]
pause