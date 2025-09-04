import pystray
from PIL import Image
from flash_copy_tool.logger import logger

class TrayIcon:
    def __init__(self, app):
        self.app = app
        self.icon = self.create_icon()
    
    def create_icon(self):
        """Создание иконки для трея"""
        # Создание простой иконки
        image = Image.new('RGB', (16, 16), color='green')
        return image
    
    def on_quit(self, icon, item):
        """Обработчик выхода"""
        logger.info("Завершение работы приложения")
        icon.stop()
        self.app.stop()
    
    def show_status(self, icon, item):
        """Показать статус"""
        # Можно реализовать окно со статусом
        pass
    
    def create_menu(self):
        """Создание меню трея"""
        return pystray.Menu(
            pystray.MenuItem("Статус", self.show_status),
            pystray.MenuItem("Выход", self.on_quit)
        )
    
    def run(self):
        """Запуск иконки в трее"""
        icon = pystray.Icon("flash_copy", self.icon, "Flash Copy Tool", self.create_menu())
        icon.run()