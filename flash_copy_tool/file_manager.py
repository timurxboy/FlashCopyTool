import os
import shutil
import time
import win32api
import win32con
from flash_copy_tool.logger import logger
from datetime import datetime
from flash_copy_tool.config import config

class FileManager:
    def __init__(self, db):
        self.db = db
        config.setup_directories()
    
    def copy_from_flash(self, source_drive, volume_name):
        """Копирование файлов с флешки согласно требованиям 1.1.2.2"""
        try:
            if not self.ensure_free_space():
                logger.warning("Недостаточно свободного места для начала копирования")
                return False

            # 1.1.2.2 - Поиск самого старого MP4 файла для даты в названии папки
            oldest_date = self.find_oldest_mp4_date(source_drive)
            
            if oldest_date is None:
                logger.warning(f"Не найдено MP4 файлов на флешке {volume_name}")
                return False
            
            # 1.1.2.2 - Создание целевой директории в формате: метка_тома+дата_старого_файла+дата_копирования
            copy_start_time = datetime.now()
            folder_name = f"{volume_name}_{oldest_date.strftime('%Y-%m-%d_%H-%M-%S')}"
            target_folder = os.path.join(config.ARCHIVE_DIR, folder_name)
            os.makedirs(target_folder, exist_ok=True)
            
            logger.info(f"Создана целевая папка: {target_folder}")
            
            # 1.1.2.2 - Копирование MP4 файлов (исключая IGNORE_PATHS)
            copied_files = self.copy_mp4_files(source_drive, target_folder, volume_name)
            
            if copied_files > 0:
                # 1.1.2.3 - Очистка флешки после копирования
                self.clean_flash_drive(source_drive)
                
                logger.info(f"Скопировано {copied_files} файлов с {volume_name}")
                return True
            else:
                logger.warning(f"Не найдено MP4 файлов на {volume_name}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка копирования с {volume_name}: {e}")
            return False
    
    def find_oldest_mp4_date(self, drive_path):
        """Поиск даты создания самого старого MP4 файла"""
        oldest_date = None
        
        for root, dirs, files in os.walk(drive_path):
            # Пропуск игнорируемых путей
            dirs[:] = [d for d in dirs if not self.should_ignore_path(root, d)]
            
            for file in files:
                if file.lower().endswith('.mp4'):
                    file_path = os.path.join(root, file)
                    try:
                        created_time = datetime.fromtimestamp(os.path.getctime(file_path))
                        if oldest_date is None or created_time < oldest_date:
                            oldest_date = created_time
                    except Exception as e:
                        logger.warning(f"Не удалось получить время создания файла {file_path}: {e}")
                        continue
        
        return oldest_date
    
    def copy_mp4_files(self, source_drive, target_folder, volume_name):
        """Копирование MP4 файлов в одну папку, пропуская дубликаты"""
        copied_count = 0
        
        for root, dirs, files in os.walk(source_drive):
            # Пропуск игнорируемых путей
            dirs[:] = [d for d in dirs if not self.should_ignore_path(root, d)]
            
            for file in files:
                if file.lower().endswith('.mp4'):
                    if self.db.file_exists(volume_name, file):
                        logger.info(f"Пропускаем дубликат: {file} уже существует")
                        continue

                    # ✅ ПРОВЕРКА МЕСТА ПЕРЕД КАЖДЫМ ФАЙЛОМ
                    if not self.ensure_free_space():
                        logger.error("Не удалось обеспечить достаточно свободного места, прерывание копирования")
                        return copied_count
                    source_file = os.path.join(root, file)
                    
                    try:
                        # Копируем файл прямо в целевую папку
                        dest_file = os.path.join(target_folder, file)
                        
                        shutil.copy2(source_file, dest_file)

                        dir_name = os.path.basename(target_folder)
                        created_time = datetime.fromtimestamp(os.path.getctime(source_file))
                        self.db.add_file(volume_name, dir_name, file, dest_file, created_time)
                        
                        copied_count += 1
                        logger.info(f"Скопирован: {file}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка копирования {file}: {e}")
        
        return copied_count
    
    def should_ignore_path(self, root_path, dir_name):
        """Проверка, нужно ли игнорировать путь согласно IGNORE_PATHS"""
        full_path = os.path.join(root_path, dir_name).replace('\\', '/')
        ignore_paths = [ip.strip() for ip in config.IGNORE_PATHS if ip.strip()]
        return any(ignore_path in full_path for ignore_path in ignore_paths)
    
    def clean_flash_drive(self, drive_path):
        """Очистка флешки от MP4 файлов (1.1.2.3)"""
        deleted_count = 0
        try:
            for root, dirs, files in os.walk(drive_path):
                # Пропуск игнорируемых путей
                dirs[:] = [d for d in dirs if not self.should_ignore_path(root, d)]
                
                for file in files:
                    if file.lower().endswith('.mp4'):
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                            logger.info(f"Удален с флешки: {file_path}")
                        except Exception as e:
                            logger.error(f"Ошибка удаления {file_path}: {e}")
            
            logger.info(f"Удалено {deleted_count} файлов с флешки")
            
        except Exception as e:
            logger.error(f"Ошибка очистки флешки: {e}")
    


    def ensure_free_space(self):
        """Гарантирует наличие свободного места, удаляя отправленные файлы"""
        try:
            while True:
                usage = shutil.disk_usage(config.ROOT_DIR)
                total_space = usage.total
                used_space = usage.used
                free_space = usage.free

                logger.info(
                    f"Диск для ROOT_DIR: {config.ROOT_DIR}\n"
                    f"Общий размер: {total_space} байт ({total_space / (1024**3):.2f} ГБ)\n"
                    f"Использовано: {used_space} байт ({used_space / (1024**3):.2f} ГБ)\n"
                    f"Свободно: {free_space} байт ({free_space / (1024**3):.2f} ГБ)\n"
                    f"Минимум по конфигу: {config.MINIMUM_FREE_MEMORY} байт "
                    f"({config.MINIMUM_FREE_MEMORY / (1024**3):.2f} ГБ)"
                )
                
                if free_space >= config.MINIMUM_FREE_MEMORY:
                    return True  # ✅ Места хватает, выходим

                logger.warning(
                    f"Мало свободного места: {free_space / (1024**3):.2f} ГБ < "
                    f"{config.MINIMUM_FREE_MEMORY / (1024**3):.2f} ГБ"
                )

                # Пытаемся удалить старые отправленные файлы
                deleted_count = self.delete_oldest_uploaded_files()
                if deleted_count > 0:
                    continue  # Проверим снова сразу после удаления

                
                usage = shutil.disk_usage(config.ROOT_DIR)
                if usage.free >= config.MINIMUM_FREE_MEMORY:
                    logger.info("Появилось свободное место во время ожидания")
                    return True

                logger.info("Место не появилось, пробуем снова...")
                win32api.MessageBox(
                    0,
                    "Недостаточно свободного места!\n\n"
                    f"Свободно: {free_space / (1024**3):.2f} ГБ\n"
                    f"Требуется минимум: {config.MINIMUM_FREE_MEMORY / (1024**3):.2f} ГБ\n\n"
                    "Освободите место на диске и нажмите OK для продолжения.",
                    "Ошибка: Нет места",
                    win32con.MB_ICONERROR | win32con.MB_OK
                )
                time.sleep(5)  # Ждем перед следующей попыткой
            
        except Exception as e:
            logger.error(f"Ошибка освобождения места: {e}")
            return False
    
    def delete_oldest_uploaded_files(self):
        """Удаление самых старых ОТПРАВЛЕННЫХ файлов и возврат количества удаленных"""
        try:
            # Получаем самые старые отправленные файлы
            old_uploaded_files = self.db.get_oldest_uploaded_files()
            
            if not old_uploaded_files:
                logger.warning("Нет отправленных файлов для удаления")
                return 0
                
            deleted_count = 0
            for file_id, file_path in old_uploaded_files:
                try:
                    # Удаляем файл с диска
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        logger.info(f"Удален отправленный файл: {file_path} ({file_size} байт)")
                    
                    # Удаляем запись из БД
                    self.db.delete_file(file_id)
                    deleted_count += 1
                    
                    # Логируем прогресс
                    logger.debug(f"Удалено файлов: {deleted_count}")
                    
                except Exception as e:
                    logger.error(f"Ошибка удаления файла {file_path}: {e}")
                    continue
            
            logger.info(f"Удалено {deleted_count} отправленных файлов")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка удаления старых файлов: {e}")
            return 0