@echo off
chcp 65001 >nul
echo [=== Установка FlashCopyTool в автозагрузку ===]

:: Проверяем права администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Запустите этот файл от имени администратора!
    pause
    exit /b 1
)

:: Создаем папку в Program Files
echo Создаем папку программы...
mkdir "C:\Program Files\FlashCopyTool" 2>nul

:: Копируем exe файл
echo Копируем программу...
copy /Y "%~dp0FlashCopyTool.exe" "C:\Program Files\FlashCopyTool\" >nul
copy /Y "%~dp0uninstall.bat" "C:\Program Files\FlashCopyTool\" >nul

:: Проверка, что FlashCopyTool.exe скопировался
if not exist "C:\Program Files\FlashCopyTool\FlashCopyTool.exe" (
    echo [ОШИБКА] Не найден FlashCopyTool.exe рядом с install.bat!
    pause
    exit /b 1
)

:: Проверка, что uninstall.bat скопировался
if not exist "C:\Program Files\FlashCopyTool\uninstall.bat" (
    echo [ОШИБКА] Файл uninstall.bat не найден рядом с install.bat!
    pause
    exit /b 1
)

:: Создаем стандартный .env файл если его нет
echo Проверяем файл настроек...
if not exist "C:\Program Files\FlashCopyTool\.env" (
    echo Создаем стандартный .env файл...
    (
        echo # AWS S3 Settings
        echo ACCESS_KEY_ID=
        echo SECRET_ACCESS_KEY=
        echo STORAGE_BUCKET_NAME=
        echo S3_ENDPOINT_URL=
        echo S3_REGION_NAME=
        echo.
        echo # System Settings
        echo MINIMUM_FREE_MEMORY=100GB
        echo IGNORE_PATHS=/tmp
        echo SCAN_TIMEOUT=5000
        echo ROOT_DIR=
        echo.
        echo # Logging Configuration
        echo LOG_LEVEL=INFO
        echo LOG_FILENAME=flash_copy.log
        echo LOG_BACKUP_COUNT=7
    ) > "C:\Program Files\FlashCopyTool\.env"
) else (
    echo Файл настроек уже существует.
)

:: Создаем ярлык в автозагрузке
echo Добавляем в автозагрузку...
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\create_shortcut.vbs"
echo sLinkFile = "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\FlashCopyTool.lnk" >> "%TEMP%\create_shortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\create_shortcut.vbs"
echo oLink.TargetPath = "C:\Program Files\FlashCopyTool\FlashCopyTool.exe" >> "%TEMP%\create_shortcut.vbs"
echo oLink.WorkingDirectory = "C:\Program Files\FlashCopyTool\" >> "%TEMP%\create_shortcut.vbs"
echo oLink.Description = "Flash Copy Tool" >> "%TEMP%\create_shortcut.vbs"
echo oLink.WindowStyle = 7 >> "%TEMP%\create_shortcut.vbs"
echo oLink.Save >> "%TEMP%\create_shortcut.vbs"

cscript //nologo "%TEMP%\create_shortcut.vbs" >nul
del "%TEMP%\create_shortcut.vbs" 2>nul

:: Создаем службу Windows (альтернативный вариант)
echo Создаем службу Windows...
sc create FlashCopyTool binPath= "C:\Program Files\FlashCopyTool\FlashCopyTool.exe" start= auto DisplayName= "Flash Copy Tool" >nul 2>&1

echo.
echo [=== Установка завершена! ===]
echo.
echo Программа установлена в: C:\Program Files\FlashCopyTool\
echo Файл настроек: C:\Program Files\FlashCopyTool\.env
echo 
echo.
echo Программа будет автоматически запускаться при загрузке Windows.
echo.
echo Для изменения настроек отредактируйте файл .env
echo.
pause