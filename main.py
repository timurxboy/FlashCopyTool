import sys
import os
from flash_copy_tool.logger import Logger, logger
from flash_copy_tool.config import config
import threading

# Добавляем путь к текущей директории для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

config.ROOT_DIR

try:
    from flash_copy_tool.config import config
    from flash_copy_tool.database import Database
    from flash_copy_tool.usb_monitor import USBMonitor
    from flash_copy_tool.s3_uploader import S3Uploader
    
    class FlashCopyApp:
        def __init__(self):
            # Сначала настраиваем логирование
            Logger()  # Инициализация логгера

            # Теперь инициализируем конфиг (проверится .env)
            self.logger = logger
            self.logger.info("Проверка конфигурации...")
            
            # Принудительно загружаем конфиг для проверки
            _ = config.ACCESS_KEY_ID  # Это вызовет проверку .env
            
            self.db = Database()
            self.monitor = USBMonitor(self.db)
            self.uploader = S3Uploader(self.db)
            self.running = False
        
        def start(self):
            """Запуск приложения"""
            try:
                self.logger.info("Запуск Flash Copy Tool")
                self.running = True
                
                # Запуск мониторинга USB
                self.monitor.start_monitoring()
                
                # Запуск сервиса загрузки
                self.uploader.start_upload_service()
                
                self.logger.info("Приложение запущено и работает в фоновом режиме")
                
                # Основной цикл (бесконечный)
                while self.running:
                    threading.Event().wait(60)  # Проверка каждую минуту
                    
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                self.logger.error(f"Критическая ошибка: {e}")
                self.stop()
        
        def stop(self):
            """Остановка приложения"""
            self.logger.info("Остановка приложения")
            self.running = False
            sys.exit(0)

    if __name__ == "__main__":

        # Скрываем консольное окно если запущено как exe
        if getattr(sys, 'frozen', False):
            import win32gui
            import win32con
            
            # Скрываем консольное окно
            window = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(window, win32con.SW_HIDE)
        
        app = FlashCopyApp()
        app.start()

except Exception as e:
    error_msg = f"Ошибка запуска приложения: {e}"
    print(error_msg)
    
    # Записываем в лог если возможно
    try:
        log_dir = os.path.join(config.ROOT_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, 'error.log'), 'a') as f:
            f.write(f"{error_msg}\n")
    except:
        pass
    
    if getattr(sys, 'frozen', False):
        input("Нажмите Enter для выхода...")
    sys.exit(1)