import json
import sys
import os
import logging
import asyncio
from telegram import Bot
from telegram.error import TelegramError

# Настройка пути для импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.abstractions import AbstractExecutor
from conductor.shared.mocks import MockKafkaConsumer
from conductor.config import KAFKA_TOPIC_ACTIONS, TELEGRAM_BOT_TOKEN

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)


class ActionExecutor(AbstractExecutor):
    """
    Исполнитель, который потребляет команды из Kafka и выполняет их,
    поддерживая асинхронную отправку сообщений в Telegram.
    """

    def __init__(self):
        self.kafka_consumer = MockKafkaConsumer(KAFKA_TOPIC_ACTIONS)
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN':
            logger.warning("Токен для Telegram-бота не установлен. Отправка в Telegram будет невозможна.")
            self.telegram_bot = None
        else:
            self.telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)
        logger.info("ActionExecutor инициализирован.")
        # Создаем новый цикл событий для асинхронных задач
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def start(self):
        """
        Основной цикл для исполнителя. Потребляет команды из Kafka
        и выполняет их.
        """
        logger.info("Запуск ActionExecutor...")
        for message in self.kafka_consumer:
            try:
                command_data = json.loads(message.value)
                action = command_data.get("action")
                target = command_data.get("target")
                text = command_data.get("text")
                chat_id = command_data.get("chat_id")
                platform = command_data.get("platform", "whatsapp")

                if not all([action, target, chat_id, text]):
                    logger.warning("Получена неполная команда, пропускаю.", extra={"command": command_data})
                    continue

                logger.info("Получена команда на исполнение.", extra={"command": command_data})

                if platform == "telegram":
                    # Запускаем асинхронную задачу в цикле событий
                    self.loop.run_until_complete(self._execute_telegram_action(chat_id, text))
                else:
                    self._execute_whatsapp_action(chat_id, text)

            except json.JSONDecodeError:
                logger.error("Не удалось декодировать сообщение из Kafka.", exc_info=True)
            except Exception as e:
                logger.error(f"Произошла непредвиденная ошибка в Executor: {e}", exc_info=True)

    def _execute_whatsapp_action(self, chat_id, text):
        """Имитация выполнения действия для WhatsApp."""
        logger.info(f"Имитация отправки сообщения в WhatsApp чат {chat_id}: '{text}'")
        logger.info("Действие для WhatsApp успешно завершено.", extra={"chat_id": chat_id})

    async def _execute_telegram_action(self, chat_id, text):
        """Асинхронно отправляет сообщение в Telegram."""
        if not self.telegram_bot:
            logger.error("Невозможно отправить сообщение в Telegram: токен не настроен.")
            return

        try:
            logger.info(f"Отправка сообщения в Telegram чат {chat_id}: '{text}'")
            await self.telegram_bot.send_message(chat_id=chat_id, text=text)
            logger.info("Сообщение в Telegram успешно отправлено.", extra={"chat_id": chat_id})
        except TelegramError as e:
            logger.error(f"Ошибка при отправке сообщения в Telegram для chat_id {chat_id}: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        from conductor.logging_config import setup_logging
        setup_logging()
    except ImportError:
        logging.basicConfig(level=logging.INFO)

    executor = ActionExecutor()
    executor.start()