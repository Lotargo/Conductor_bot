import json
import time
import base64
import sys
import os
import logging

# Настройка пути для импорта из родительской директории
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.mocks import MockKafkaProducer
from conductor.config import KAFKA_TOPIC_NOTIFICATIONS

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)

producer = MockKafkaProducer()

def trigger_screenshot(chat_id: str):
    """
    Имитирует создание скриншота для заданного chat_id и
    отправляет данные в топик Kafka.
    """
    try:
        logger.info(f"Запуск создания скриншота для chat_id: {chat_id}")

        # Имитация создания скриншота (простой текст в качестве заглушки)
        fake_image_data = f"screenshot_for_{chat_id}_{time.time()}".encode('utf-8')
        base64_image = base64.b64encode(fake_image_data).decode('utf-8')

        message = {
            "chat_id": chat_id,
            "timestamp": time.time(),
            "screenshot_base64": base64_image
        }

        # Отправка сообщения в Kafka
        producer.send(
            KAFKA_TOPIC_NOTIFICATIONS,
            value=json.dumps(message)
        )
        producer.flush()
        logger.info(f"Уведомление о скриншоте для chat_id: {chat_id} отправлено в Kafka.")
    except Exception as e:
        logger.error(f"Ошибка при создании или отправке скриншота для chat_id {chat_id}: {e}", exc_info=True)