import json
import time
from collections import defaultdict
import threading
import sys
import os
import logging

# Настройка пути для импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.mocks import MockKafkaConsumer, MockKafkaProducer, MockRAGDatabase
from conductor.config import (
    KAFKA_TOPIC_WHATSAPP_NOTIFICATIONS,
    KAFKA_TOPIC_TELEGRAM_NOTIFICATIONS,
    KAFKA_TOPIC_DECISIONS,
    ORCHESTRATOR_TIMEOUT
)

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)

# Потокобезопасные хранилища в памяти
ACTIVE_TIMERS = {}
SCREENSHOT_BUFFER = defaultdict(list)
lock = threading.Lock()

# Инициализация мок-компонентов
producer = MockKafkaProducer()
rag_db = MockRAGDatabase()

def load_persona_manifest(persona_name: str = "corporate_assistant"):
    """Загружает манифест персоны."""
    # ... (код остался без изменений)
    current_dir = os.path.dirname(__file__)
    personas_dir = os.path.abspath(os.path.join(current_dir, '..', 'personas'))
    manifest_path = os.path.join(personas_dir, f"{persona_name}.json")
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"system_prompt": "You are a helpful assistant."}


def process_timeout(chat_id: str):
    """
    Вызывается по тайм-ауту для сборки данных и отправки в decision engine.
    """
    with lock:
        logger.info(f"Тайм-аут для chat_id: {chat_id}. Начинаю обработку...")
        screenshots_data = SCREENSHOT_BUFFER.pop(chat_id, [])
        if not screenshots_data:
            logger.warning(f"Нет данных для обработки для chat_id: {chat_id}.")
            ACTIVE_TIMERS.pop(chat_id, None)
            return

        try:
            # Платформа определяется по первому сообщению в серии
            platform = screenshots_data[0].get("platform", "whatsapp")
            screenshots_base64 = [msg["screenshot_base64"] for msg in screenshots_data]
            persona_manifest = load_persona_manifest()
            rag_context = rag_db.get_history(chat_id)

            decision_request = {
                "chat_id": chat_id,
                "platform": platform, # Передаем платформу дальше
                "persona_manifest": persona_manifest,
                "rag_context": rag_context,
                "screenshots": screenshots_base64
            }

            producer.send(KAFKA_TOPIC_DECISIONS, value=json.dumps(decision_request))
            producer.flush()
            logger.info(f"Запрос на принятие решения для chat_id: {chat_id} (платформа: {platform}) отправлен.")

        except Exception as e:
            logger.error(f"Ошибка при обработке тайм-аута для chat_id {chat_id}: {e}", exc_info=True)
        finally:
            ACTIVE_TIMERS.pop(chat_id, None)

def handle_notification(data):
    """
    Обрабатывает одно уведомление: сохраняет в буфер и управляет таймером.
    """
    chat_id = data.get("chat_id")
    if not chat_id:
        logger.warning("Получено сообщение без chat_id, пропускаю.")
        return

    logger.info(f"Получено уведомление для chat_id: {chat_id} с платформы {data.get('platform')}")

    with lock:
        SCREENSHOT_BUFFER[chat_id].append(data)

        if chat_id not in ACTIVE_TIMERS:
            logger.info(f"Запуск нового таймера для chat_id: {chat_id}")
            timer = threading.Timer(ORCHESTRATOR_TIMEOUT, process_timeout, args=[chat_id])
            ACTIVE_TIMERS[chat_id] = timer
            timer.start()
        else:
            logger.info(f"Таймер для chat_id: {chat_id} уже активен. Буферизация данных.")

def consume_topic(topic: str):
    """
    Цикл, который слушает один топик Kafka и передает сообщения в обработчик.
    """
    consumer = MockKafkaConsumer(topic)
    logger.info(f"Оркестратор начинает слушать топик: {topic}")
    for message in consumer:
        try:
            data = json.loads(message.value)
            handle_notification(data)
        except json.JSONDecodeError:
            logger.error(f"Не удалось декодировать сообщение из топика {topic}.", exc_info=True)
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в потребителе для топика {topic}: {e}", exc_info=True)

def run_orchestrator():
    """
    Запускает два потока-потребителя для прослушивания уведомлений
    от WhatsApp и Telegram.
    """
    logger.info("Запуск Orchestrator с поддержкой нескольких платформ...")

    whatsapp_thread = threading.Thread(target=consume_topic, args=(KAFKA_TOPIC_WHATSAPP_NOTIFICATIONS,))
    telegram_thread = threading.Thread(target=consume_topic, args=(KAFKA_TOPIC_TELEGRAM_NOTIFICATIONS,))

    whatsapp_thread.daemon = True
    telegram_thread.daemon = True

    whatsapp_thread.start()
    telegram_thread.start()

    # Потоки работают в фоне, основной поток может завершиться или ждать их
    whatsapp_thread.join()
    telegram_thread.join()

if __name__ == "__main__":
    try:
        from conductor.logging_config import setup_logging
        setup_logging()
    except ImportError:
        logging.basicConfig(level=logging.INFO)
    run_orchestrator()