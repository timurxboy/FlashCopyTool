import ctypes
from flash_copy_tool.logger import logger

class Notification:
    def __init__(self):
        self.user32 = ctypes.windll.user32
    
    def show_info(self, message, title="Flash Copy Tool"):
        """Показать информационное сообщение"""
        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
            logger.info(f"Уведомление: {title} - {message}")
        except Exception as e:
            logger.error(f"Ошибка показа уведомления: {e}")
    
    def ask_confirmation(self, title, message):
        """Запрос подтверждения"""
        try:
            result = ctypes.windll.user32.MessageBoxW(0, message, title, 0x34)
            return result == 6  # IDYES = 6
        except Exception as e:
            logger.error(f"Ошибка запроса подтверждения: {e}")
            return False
    
    def show_tray_notification(self, title, message):
        """Показать уведомление в системном трее"""
        try:
            # Использование Windows API для toast уведомлений
            pass
        except Exception as e:
            logger.error(f"Ошибка tray уведомления: {e}")