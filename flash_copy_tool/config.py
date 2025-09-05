import os
import sys


class Config:
    # Базовые пути
    if getattr(sys, 'frozen', False):
        # Если запущено как exe файл
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        # Если запущено как скрипт
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Путь к .env файлу - рядом с exe файлом
    ENV_PATH = os.path.join(BASE_DIR, '.env')
    
    # Загружаем переменные окружения из .env файла
    def _load_env(self):
        env_vars = {}
        try:
            if not os.path.exists(self.ENV_PATH):
                error_msg = f"Файл .env не найден: {self.ENV_PATH}\nСоздайте файл .env с настройками."
                print(error_msg)
                if getattr(sys, 'frozen', False):
                    input("Нажмите Enter для выхода...")
                sys.exit(1)
            
            with open(self.ENV_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
            
            # Все обязательные поля
            required_fields = [
                'ACCESS_KEY_ID', 'SECRET_ACCESS_KEY', 'STORAGE_BUCKET_NAME',
                'S3_ENDPOINT_URL', 'S3_REGION_NAME', 'MINIMUM_FREE_MEMORY',
                'IGNORE_PATHS', 'SCAN_TIMEOUT',
                'LOG_LEVEL', 'LOG_FILENAME', 'LOG_BACKUP_COUNT'
            ]
            
            # Проверяем, что поле есть и не пустое
            missing_fields = [field for field in required_fields if not env_vars.get(field)]
            
            if missing_fields:
                error_msg = f"Отсутствуют или пустые обязательные поля в .env: {', '.join(missing_fields)}"
                print(error_msg)
                if getattr(sys, 'frozen', False):
                    input("Нажмите Enter для выхода...")
                sys.exit(1)
                    
        except Exception as e:
            error_msg = f"Критическая ошибка загрузки .env файла: {e}"
            print(error_msg)
            if getattr(sys, 'frozen', False):
                input("Нажмите Enter для выхода...")
            sys.exit(1)
        
        return env_vars
    
    def __init__(self):
        # Не загружаем env сразу, только при первом обращении
        self.env_vars = None
        self._loaded = False
    
    def _ensure_loaded(self):
        """Убедиться, что конфиг загружен"""
        if not self._loaded:
            self.env_vars = self._load_env()
            self._loaded = True
    
    def get(self, key, default=None):
        self._ensure_loaded()
        return self.env_vars.get(key, default)
    
    # AWS S3 параметры
    @property
    def ACCESS_KEY_ID(self):
        return self.get('ACCESS_KEY_ID')
    
    @property
    def SECRET_ACCESS_KEY(self):
        return self.get('SECRET_ACCESS_KEY')
    
    @property
    def STORAGE_BUCKET_NAME(self):
        return self.get('STORAGE_BUCKET_NAME')
    
    @property
    def S3_ENDPOINT_URL(self):
        return self.get('S3_ENDPOINT_URL')
    
    @property
    def S3_REGION_NAME(self):
        return self.get('S3_REGION_NAME')
    
    @property
    def UNIT_NAME(self):
        return self.get('UNIT_NAME')

    # Параметры системы
    @property
    def MINIMUM_FREE_MEMORY(self):
        return self._parse_size(self.get('MINIMUM_FREE_MEMORY'))
    
    @property
    def IGNORE_PATHS(self):
        return self.get('IGNORE_PATHS').split(',')
    
    @property
    def SCAN_TIMEOUT(self):
        return int(self.get('SCAN_TIMEOUT'))
    
    # Пути для данных
    # @property
    # def ROOT_DIR(self):
    #     return os.path.join(os.environ.get('APPDATA', self.BASE_DIR), 'FlashCopyTool')
    
    @property
    def ROOT_DIR(self):
        return self.get('ROOT_DIR')

    @property
    def ARCHIVE_DIR(self):
        return os.path.join(self.ROOT_DIR, 'archive')
    
    @property
    def DB_PATH(self):
        return os.path.join(self.ROOT_DIR, 'flash_copy.db')
    
    # --- Logging params ---
    @property
    def LOGGER_NAME(self):
        return self.get("LOGGER_NAME")
    
    @property
    def LOG_DIR(self):
        return os.path.join(self.ROOT_DIR, 'logs')

    @property
    def LOG_LEVEL(self):
        return self.get("LOG_LEVEL").upper()

    @property
    def LOG_FILENAME(self):
        return self.get("LOG_FILENAME")

    @property
    def LOG_BACKUP_COUNT(self):
        return int(self.get("LOG_BACKUP_COUNT"))

    
    def _parse_size(self, size_str):
        """Парсинг размера из строки в байты"""
        if isinstance(size_str, int):
            return size_str
            
        size_str = str(size_str).upper().strip()
        size_str = size_str.replace(' ', '')
        
        if size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        else:
            try:
                return int(size_str)
            except ValueError:
                return 100 * 1024 * 1024 * 1024  # 100GB по умолчанию
    
    def setup_directories(self):
        """Создание необходимых директорий"""
        try:
            os.makedirs(self.ROOT_DIR, exist_ok=True)
            os.makedirs(self.ARCHIVE_DIR, exist_ok=True)
        except Exception as e:
            print(f"Ошибка создания директорий: {e}")

# Глобальный экземпляр конфига (но пока не загружаем)
config = Config()
