from datetime import datetime
import boto3
import os
import time
from threading import Thread
from flash_copy_tool.logger import logger
from botocore.exceptions import ClientError, NoCredentialsError, ConnectionError
from flash_copy_tool.config import config

class S3Uploader:
    def __init__(self, db):
        self.db = db
        self.s3_client = self.create_s3_client()
        self.uploading = False
        self.app_start_time = time.time()
        self.last_scan_time = 0
        self.known_folders = set()
    
    def create_s3_client(self):
        """Создание S3 клиента с обработкой ошибок"""
        try:
            return boto3.client(
                's3',
                endpoint_url=config.S3_ENDPOINT_URL,
                region_name=config.S3_REGION_NAME,
                aws_access_key_id=config.ACCESS_KEY_ID,
                aws_secret_access_key=config.SECRET_ACCESS_KEY,
                config=boto3.session.Config(connect_timeout=30, retries={'max_attempts': 3})
            )
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            return None
        except Exception as e:
            logger.error(f"Ошибка создания S3 клиента: {e}")
            return None
    
    def check_for_new_files(self):
        """Проверка новых файлов в архиве"""
        try:
            if not os.path.exists(config.ARCHIVE_DIR):
                return 0

            added_files = 0
            for root, _, files in os.walk(config.ARCHIVE_DIR):
                for file in files:
                    if file.lower().endswith(".mp4"):
                        file_path = os.path.join(root, file)

                        try:
                            # Берем время последней модификации
                            mtime = os.path.getmtime(file_path)
                            age = datetime.now().timestamp() - mtime

                            # Берем размер файла
                            size1 = os.path.getsize(file_path)
                            time.sleep(1)  # небольшая пауза
                            size2 = os.path.getsize(file_path)

                            # Условие: файл старше 60 сек и не меняет размер
                            if age > 60 and size1 == size2:
                                added_files += self.db.scan_specific_file(file_path)

                        except Exception as fe:
                            logger.warning(f"Не удалось проверить файл {file_path}: {fe}")

            return added_files

        except Exception as e:
            logger.error(f"Ошибка проверки файлов: {e}")
            return 0
    
    def upload_file(self, file_id, dir_name, file_name, file_path):
        """Загрузка файла на S3 с обработкой ошибок сети"""
        max_retries = 5
        retry_delay = 10  # seconds
        
        for attempt in range(max_retries):
            try:
                # Отмечаем начало загрузки
                self.db.mark_upload_started(file_id)
                
                # Формирование S3 пути: device_name/file_name
                s3_path = f"{dir_name}/{file_name}"
                
                # Загрузка файла
                self.s3_client.upload_file(
                    file_path, 
                    config.STORAGE_BUCKET_NAME, 
                    s3_path,
                    ExtraArgs={'ContentType': 'video/mp4'}
                )
                
                # Отмечаем завершение загрузки
                self.db.mark_upload_completed(file_id)
                
                logger.info(f"Файл загружен на S3: {s3_path}")
                return True
                
            except (ClientError, ConnectionError) as e:
                error_msg = str(e)
                logger.error(f"Ошибка сети S3 (попытка {attempt + 1}/{max_retries}): {error_msg}")
                
                # Проверяем, является ли ошибка временной
                if self.is_temporary_error(error_msg) and attempt < max_retries - 1:
                    sleep_time = retry_delay * (attempt + 1)
                    logger.info(f"Повторная попытка через {sleep_time} секунд...")
                    time.sleep(sleep_time)
                else:
                    return False
                    
            except Exception as e:
                logger.error(f"Неожиданная ошибка при загрузке (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    return False
        
        return False
    
    def is_temporary_error(self, error_msg):
        """Проверка, является ли ошибка временной"""
        temporary_errors = [
            'timeout', 'timed out', 'connection', 'network', 'temporary',
            'retry', 'throttl', 'rate exceeded', 'slow down'
        ]
        return any(keyword in error_msg.lower() for keyword in temporary_errors)
    
    def scan_and_upload(self):
        """Сканирование и загрузка файлов"""
        if not self.s3_client:
            logger.warning("S3 клиент не инициализирован, пропускаем загрузку")
            return
        
        try:
            # Берём все файлы, которые ещё не загружены
            pending_files = self.db.get_pending_files(self.app_start_time)
            
            if not pending_files:
                logger.debug("Нет файлов для загрузки")
                return
            
            logger.info(f"Найдено {len(pending_files)} файлов для загрузки")
            
            uploaded_count = 0
            failed_count = 0
            
            for file_id, dir_name, file_name, file_path in pending_files:
                if os.path.exists(file_path):
                    logger.info(f"Начало загрузки: {file_name}")
                    success = self.upload_file(file_id, dir_name, file_name, file_path)
                    
                    if success:
                        uploaded_count += 1
                    else:
                        failed_count += 1
                else:
                    logger.warning(f"Файл не найден: {file_path}")
                    failed_count += 1
            
            # Очистка отсутствующих файлов из БД
            self.db.cleanup_missing_files()
            
            if uploaded_count > 0 or failed_count > 0:
                logger.info(f"Загрузка завершена. Успешно: {uploaded_count}, Ошибок: {failed_count}")
            
        except Exception as e:
            logger.error(f"Ошибка сканирования: {e}")
    
    def start_upload_service(self):
        """Запуск сервиса загрузки"""
        def upload_loop():
            while True:
                try:
                    if not self.uploading:
                        self.uploading = True
                        self.scan_and_upload()
                        self.uploading = False
                    
                    # Задержка между сканами
                    time.sleep(config.SCAN_TIMEOUT / 1000)
                    
                except Exception as e:
                    logger.error(f"Ошибка в сервисе загрузки: {e}")
                    self.uploading = False
                    time.sleep(60)
        
        upload_thread = Thread(target=upload_loop, daemon=True)
        upload_thread.start()
        logger.info("Сервис загрузки на S3 запущен")

        # Инициализируем известные папки
        self.check_for_new_files()