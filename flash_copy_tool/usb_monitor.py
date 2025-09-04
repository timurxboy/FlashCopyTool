import time
import win32api
import win32file
from threading import Thread
from flash_copy_tool.logger import logging
from flash_copy_tool.file_manager import FileManager
from flash_copy_tool.notification import Notification

class USBMonitor:
    def __init__(self, db):
        self.db = db
        self.file_manager = FileManager(db)
        self.notification = Notification()
        self.known_drives = set()
        self.failed_drives = set() # Для хранения дисков с ошибками доступа
    
    def get_flash_drives(self):
        """Получение списка флеш-накопителей с метками"""
        drives = []
        for drive in win32api.GetLogicalDriveStrings().split('\x00'):
            if drive and drive.strip():
                drive = drive.strip()
                try:
                    if win32file.GetDriveType(drive) == win32file.DRIVE_REMOVABLE:
                        try:
                            vol_name, _, _, _, _ = win32api.GetVolumeInformation(drive)

                            # если диск был битый — пишем восстановление
                            if drive in self.failed_drives:
                                logging.info(f"Диск {drive} снова доступен")
                                self.failed_drives.remove(drive)

                            if vol_name:
                                drives.append((drive, vol_name))
                            else:
                                logging.info(f"Диск {drive} не имеет метки тома, пропускаем")

                        except Exception as e:
                            # логируем только при первом сбое
                            if drive not in self.failed_drives:
                                logging.warning(f"Не удалось получить информацию о диске {drive}: {e}")
                                self.failed_drives.add(drive)
                            continue
                except Exception as e:
                    logging.error(f"Ошибка проверки типа диска {drive}: {e}")
        return drives
    
    def check_new_drives(self):
        """Проверка новых USB устройств"""
        try:
            current_drives = self.get_flash_drives()
            new_drives = [d for d in current_drives if d not in self.known_drives]
            
            for drive, vol_name in new_drives:
                self.handle_new_drive(drive, vol_name)
            
            self.known_drives = set(current_drives)
            
        except Exception as e:
            logging.error(f"Ошибка проверки дисков: {e}")
    
    def handle_new_drive(self, drive, vol_name):
        """Обработка нового USB устройства согласно требованиям"""
        try:
            # 1.1 - Проверяем, известно ли устройство в БД
            is_known = self.db.is_device_known(vol_name)
            
            if is_known:
                # 1.2 - Известное устройство: автоматическое копирование
                logging.info(f"Автоматическое копирование с известного устройства: {vol_name}")
                self.notification.show_info(f"Копирование с {vol_name} начато")
                
                # 1.1.2.2 - Начинаем процесс копирования
                success = self.file_manager.copy_from_flash(drive, vol_name)
                
                if success:
                    # 1.1.2.3 - После завершения копирования выводим сообщение
                    self.notification.show_info(f"Копирование с {vol_name} завершено. Можно извлекать флешку.")
                else:
                    self.notification.show_info(f"Ошибка копирования с {vol_name}")
                
            else:
                # 1.1 - Неизвестное устройство: запрос подтверждения
                response = self.notification.ask_confirmation(
                    f"{vol_name} обнаружена",
                    f"Нужно ли начать перенос данных с флешки '{vol_name}'?"
                )
                
                if response:
                    # 1.1.2 - Пользователь подтвердил
                    # 1.1.2.1 - Добавляем устройство в БД
                    if self.db.add_device(vol_name):
                        logging.info(f"Добавлено новое устройство: {vol_name}")
                        
                        # 1.1.2.2 - Начинаем процесс копирования
                        self.notification.show_info(f"Копирование с {vol_name} начато")
                        success = self.file_manager.copy_from_flash(drive, vol_name)
                        
                        if success:
                            # 1.1.2.3 - После завершения копирования выводим сообщение
                            self.notification.show_info(f"Копирование с {vol_name} завершено. Можно извлекать флешку.")
                        else:
                            self.notification.show_info(f"Ошибка копирования с {vol_name}")
                    else:
                        self.notification.show_info(f"Ошибка добавления устройства {vol_name}")
                else:
                    # 1.1.1 - Пользователь отказался
                    logging.info(f"Пользователь отказался от копирования с {vol_name}")
                    self.notification.show_info(f"Копирование с {vol_name} отменено")
                    
        except Exception as e:
            logging.error(f"Ошибка обработки устройства {vol_name}: {e}")
            self.notification.show_info(f"Ошибка обработки устройства {vol_name}")
    
    def start_monitoring(self):
        """Запуск мониторинга USB"""
        def monitor_loop():
            while True:
                try:
                    self.check_new_drives()
                    time.sleep(5)  # Проверка каждые 5 секунд
                except Exception as e:
                    logging.error(f"Ошибка мониторинга USB: {e}")
                    time.sleep(10)
        
        monitor_thread = Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logging.info("Мониторинг USB устройств запущен")