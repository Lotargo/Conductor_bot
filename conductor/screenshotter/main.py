import json
import time
import base64
import sys
import os
import logging

# Настройка пути для импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.mocks import MockKafkaProducer
from conductor.config import (
    KAFKA_TOPIC_WHATSAPP_NOTIFICATIONS,
    KAFKA_TOPIC_TELEGRAM_NOTIFICATIONS
)

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)

producer = MockKafkaProducer()

def trigger_screenshot(chat_id: str, platform: str = "whatsapp"):
    """
    Имитирует создание "скриншота" для заданного chat_id и
    отправляет данные в соответствующий топик Kafka в зависимости от платформы.
    """
    try:
        logger.info(f"Запуск создания 'скриншота' для chat_id: {chat_id} на платформе: {platform}")

        # Выбираем топик Kafka в зависимости от платформы
        if platform == "telegram":
            topic = KAFKA_TOPIC_TELEGRAM_NOTIFICATIONS
        else:
            topic = KAFKA_TOPIC_WHATSAPP_NOTIFICATIONS

        # Имитация создания скриншота
        fake_image_data = f"screenshot_for_{chat_id}_on_{platform}_{time.time()}".encode('utf-8')
        base64_image = base64.b64encode(fake_image_data).decode('utf-8')

        message = {
            "chat_id": chat_id,
            "platform": platform,  # Добавляем платформу в сообщение
            "timestamp": time.time(),
            "screenshot_base64": base64_image
        }

        # Отправка сообщения в Kafka
        producer.send(topic, value=json.dumps(message))
        producer.flush()
        logger.info(f"Уведомление для chat_id: {chat_id} (платформа: {platform}) отправлено в топик {topic}.")
    except Exception as e:
        logger.error(f"Ошибка при создании или отправке уведомления для chat_id {chat_id}: {e}", exc_info=True)