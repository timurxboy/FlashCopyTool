import os
import sqlite3
from flash_copy_tool.logger import logger
from datetime import datetime
from flash_copy_tool.config import config

class Database:
    def __init__(self):
        try:
            # Убедимся, что директория существует
            os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
            
            self.conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
            logger.info(f"База данных подключена: {config.DB_PATH}")
            
            self.create_tables()
            
        except sqlite3.Error as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            raise
    
    def create_tables(self):
        """Создание таблиц БД"""
        cursor = self.conn.cursor()
        
        # Таблица устройств
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices_to_copy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица файлов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                dir_name TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at DATETIME,
                upload_started_at DATETIME,
                is_uploaded BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (device_name) REFERENCES devices_to_copy (name)
            )
        ''')
        
        self.conn.commit()
        logger.info("Таблицы базы данных созданы")
    
    def add_device(self, device_name):
        """Добавление устройства в БД"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO devices_to_copy (name) VALUES (?)',
                (device_name,)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления устройства: {e}")
            return False
    
    def is_device_known(self, device_name):
        """Проверка, известно ли устройство"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM devices_to_copy WHERE name = ?', (device_name,))
        return cursor.fetchone() is not None
    
    def add_file(self, device_name, dir_name, file_name, file_path, created_at):
        """Добавление файла в БД"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO files 
                (device_name, dir_name, file_name, file_path, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (device_name, dir_name, file_name, file_path, created_at))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления файла: {e}")
            return None
    
    def get_pending_files(self, app_start_time):
        """Получение файлов для загрузки согласно 2.2"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, dir_name, file_name, file_path 
            FROM files 
            WHERE is_uploaded = FALSE 
            AND (upload_started_at IS NULL OR upload_started_at < ?)
        ''', (datetime.fromtimestamp(app_start_time),))
        return cursor.fetchall()
    
    def mark_upload_started(self, file_id):
        """Отметка начала загрузки"""
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE files SET upload_started_at = ? WHERE id = ?',
            (datetime.now(), file_id)
        )
        self.conn.commit()
    
    def mark_upload_completed(self, file_id):
        """Отметка завершения загрузки"""
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE files SET is_uploaded = TRUE WHERE id = ?',
            (file_id,)
        )
        self.conn.commit()
    
    def cleanup_missing_files(self):
        """Очистка отсутствующих файлов из БД согласно 2.4"""
        try:
            cursor = self.conn.cursor()
            
            # Получаем все файлы из БД
            cursor.execute('SELECT id, file_path FROM files WHERE is_uploaded = FALSE')
            db_files = cursor.fetchall()
            
            files_to_delete = []
            for file_id, file_path in db_files:
                if not os.path.exists(file_path):
                    files_to_delete.append(file_id)
            
            if files_to_delete:
                placeholders = ','.join('?' * len(files_to_delete))
                cursor.execute(f'''
                    DELETE FROM files 
                    WHERE id IN ({placeholders})
                ''', files_to_delete)
                self.conn.commit()
                logger.info(f"Удалено {len(files_to_delete)} отсутствующих файлов из БД")
                
        except sqlite3.Error as e:
            logger.error(f"Ошибка очистки БД: {e}")
    
    def scan_specific_file(self, file_path: str) -> int:
        """Добавление одного файла в БД, если его там нет"""
        try:
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return 0

            # Получаем уже существующие файлы в БД
            cursor = self.conn.cursor()
            cursor.execute('SELECT file_path FROM files WHERE file_path = ?', (file_path,))
            if cursor.fetchone():
                return 0  # файл уже есть в БД

            # Извлекаем имя устройства из имени родительской папки
            dir_name = os.path.basename(os.path.dirname(file_path))
            device_name = dir_name.split('_')[0]  # первая часть до "_"

            # Сохраняем время создания файла
            created_time = datetime.fromtimestamp(os.path.getctime(file_path))

            # Добавляем запись в БД
            self.add_file(device_name, dir_name, os.path.basename(file_path), file_path, created_time)
            logger.info(f"Добавлен новый файл в БД: {file_path}")

            return 1

        except Exception as e:
            logger.error(f"Ошибка при добавлении файла {file_path}: {e}")
            return 0

    def get_oldest_uploaded_files(self):
        """Получение самых старых отправленных файлов для удаления"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, file_path 
                FROM files 
                WHERE is_uploaded = TRUE 
                ORDER BY created_at ASC
            ''')
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения старых файлов: {e}")
            return []

    def delete_file(self, file_id):
        """Удаление файла из БД"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка удаления файла {file_id}: {e}")
            return False
    
    def file_exists(self, device_name, dir_name, file_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 1 FROM files 
            WHERE device_name = ? AND dir_name = ? AND file_name = ?
            LIMIT 1
        ''', (device_name, dir_name, file_name))
        return cursor.fetchone() is not None