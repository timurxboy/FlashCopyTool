import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Literal
from flash_copy_tool.config import config

logger = logging.getLogger(config.LOGGER_NAME)

class Logger:
    def __init__(self):
        self.output_dir = config.LOG_DIR
        self.level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = config.LOG_LEVEL
        self.filename: str = config.LOG_FILENAME
        self.backup_count: int = config.LOG_BACKUP_COUNT
        
        self.setup()

    def setup(self) -> logging.Logger:
        level = self.level.upper()
        log_dir = self.output_dir
        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, self.filename)
        print(f"Logging to: {log_path} at level: {level}")

        logger.setLevel(level)

        if logger.hasHandlers():
            logger.handlers.clear()

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

        file_handler = TimedRotatingFileHandler(
            filename=log_path,
            when="midnight",
            interval=1,
            backupCount=self.backup_count,
            encoding="utf-8",
            utc=False,
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger


