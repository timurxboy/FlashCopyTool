@echo off
chcp 65001 >nul
echo [=== Удаление FlashCopyTool ===]

:: Проверяем права администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Запустите этот файл от имени администратора!
    pause
    exit /b 1
)

:: Удаляем ярлык из автозагрузки
echo Удаляем из автозагрузки...
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\FlashCopyTool.lnk" 2>nul

:: Останавливаем и удаляем службу
echo Удаляем службу...
sc stop FlashCopyTool >nul 2>&1
sc delete FlashCopyTool >nul 2>&1

:: Удаляем папку с программой
echo Удаляем файлы программы...
rd /S /Q "C:\Program Files\FlashCopyTool" 2>nul

echo.
echo [=== Удаление завершено! ===]
echo.
pause