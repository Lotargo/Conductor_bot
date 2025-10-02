import sys
import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Настройка пути для импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.abstractions import AbstractListener
from conductor.screenshotter.main import trigger_screenshot
from conductor.config import TELEGRAM_BOT_TOKEN # Мы добавим это в config.py следующим шагом

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)

class TelegramListener(AbstractListener):
    """
    Слушатель, который принимает сообщения от Telegram-бота.
    """
    def __init__(self, bot_token: str):
        if not bot_token or bot_token == 'YOUR_TELEGRAM_BOT_TOKEN':
            raise ValueError("Необходимо указать токен для Telegram-бота в config.py.")
        self.application = Application.builder().token(bot_token).build()
        self._configure_handlers()

    def _configure_handlers(self):
        """Настраивает обработчики сообщений для бота."""
        message_handler_instance = MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        self.application.add_handler(message_handler_instance)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает входящее текстовое сообщение.
        """
        chat_id = update.message.chat_id
        text = update.message.text
        logger.info(f"Получено сообщение из Telegram от chat_id: {chat_id}, text: '{text}'")

        # Запускаем тот же процесс, что и для WhatsApp, но с указанием платформы
        # В будущем здесь можно передавать больше данных
        trigger_screenshot(chat_id, platform="telegram")

    def start(self):
        """
        Запускает бота в режиме long-polling.
        """
        logger.info("Запуск TelegramListener...")
        self.application.run_polling()

if __name__ == '__main__':
    # Этот блок для отладки
    # Убедитесь, что TELEGRAM_BOT_TOKEN установлен в вашем config.py
    try:
        from conductor.logging_config import setup_logging
        setup_logging()
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN':
            logger.warning("Токен для Telegram-бота не установлен. Запуск невозможен.")
        else:
            listener = TelegramListener(TELEGRAM_BOT_TOKEN)
            listener.start()
    except (ImportError, ValueError) as e:
        logging.basicConfig(level=logging.INFO)
        logger.error(f"Ошибка при запуске TelegramListener: {e}")