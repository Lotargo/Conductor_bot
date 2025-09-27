import json
import sys
import os
import logging

# Настройка пути для импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.mocks import MockKafkaConsumer
from conductor.config import KAFKA_TOPIC_ACTIONS

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)

def run_executor():
    """
    Основной цикл для исполнителя. Потребляет команды из Kafka
    и имитирует их выполнение.
    """
    consumer = MockKafkaConsumer(KAFKA_TOPIC_ACTIONS)

    logger.info("Запуск Executor...")
    for message in consumer:
        try:
            command_data = json.loads(message.value)
            action = command_data.get("action")
            target = command_data.get("target")
            text = command_data.get("text")
            chat_id = command_data.get("chat_id")

            # `text` может быть пустым, поэтому не проверяем его наличие
            if not all([action, target, chat_id]):
                logger.warning("Получена неполная команда на исполнение, пропускаю.", extra={"command": command_data})
                continue

            # Логируем полученную команду как структурированные данные для легкого парсинга
            logger.info("Получена команда на исполнение.", extra={
                "command": {
                    "chat_id": chat_id,
                    "action": action,
                    "target": target,
                    "text": text
                }
            })

            # В реальном сценарии здесь бы использовался Playwright
            logger.info("Имитация выполнения действия...")
            logger.info("Действие успешно завершено.", extra={"chat_id": chat_id, "action": action})

        except json.JSONDecodeError:
            logger.error("Не удалось декодировать сообщение из Kafka.", exc_info=True)
        except Exception as e:
            logger.error(f"Произошла непредвиденная ошибка в Executor: {e}", exc_info=True)


if __name__ == "__main__":
    # Этот блок теперь в основном для отладки
    try:
        from conductor.logging_config import setup_logging
        setup_logging()
    except ImportError:
        logging.basicConfig(level=logging.INFO)

    logger.info("Модуль Executor готов к запуску.")