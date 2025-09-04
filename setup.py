import os
import sys
from PyInstaller.__main__ import run

# Параметры для PyInstaller
opts = [
    'main.py',               # Главный файл
    '--name=FlashCopyTool',  # Имя приложения
    '--onefile',             # Собрать в один файл
    '--windowed',            # Без консоли (для фонового приложения)
    '--add-data=config.env;.',  # Добавить файл конфигурации
    '--hidden-import=win32timezone',
    '--hidden-import=boto3',
    '--hidden-import=botocore',
    '--hidden-import=sqlite3',
    '--hidden-import=logging.handlers',
    '--hidden-import=dotenv',
]

# Запуск сборки
run(opts)