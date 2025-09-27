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
    KAFKA_TOPIC_NOTIFICATIONS,
    KAFKA_TOPIC_DECISIONS,
    ORCHESTRATOR_TIMEOUT
)

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)

# Хранилище в памяти для активных таймеров и собранных скриншотов
ACTIVE_TIMERS = {}
SCREENSHOT_BUFFER = defaultdict(list)

# Инициализация мок-компонентов
producer = MockKafkaProducer()
rag_db = MockRAGDatabase()

def load_persona_manifest(persona_name: str = "corporate_assistant"):
    """Загружает манифест персоны из директории personas."""
    current_dir = os.path.dirname(__file__)
    personas_dir = os.path.abspath(os.path.join(current_dir, '..', 'personas'))
    manifest_path = os.path.join(personas_dir, f"{persona_name}.json")

    logger.info(f"Загрузка манифеста персоны из {manifest_path}")
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Манифест персоны не найден по пути: {manifest_path}")
        return {
          "persona_name": "Default",
          "system_prompt": "You are a helpful assistant.",
          "rules": {}
        }

def process_timeout(chat_id: str):
    """
    Эта функция вызывается по истечении таймера для chat_id.
    Она собирает данные, создает задачу и отправляет ее в decision engine.
    """
    logger.info(f"Тайм-аут для chat_id: {chat_id}. Начинаю обработку...")

    screenshots_data = SCREENSHOT_BUFFER.pop(chat_id, [])
    if not screenshots_data:
        logger.warning(f"Нет скриншотов для обработки для chat_id: {chat_id}.")
        ACTIVE_TIMERS.pop(chat_id, None)
        return

    try:
        screenshots_base64 = [msg["screenshot_base64"] for msg in screenshots_data]
        persona_manifest = load_persona_manifest()
        rag_context = rag_db.get_history(chat_id)

        decision_request = {
            "chat_id": chat_id,
            "persona_manifest": persona_manifest,
            "rag_context": rag_context,
            "screenshots": screenshots_base64
        }

        producer.send(KAFKA_TOPIC_DECISIONS, value=json.dumps(decision_request))
        producer.flush()
        logger.info(f"Запрос на принятие решения для chat_id: {chat_id} отправлен в Kafka.")

    except Exception as e:
        logger.error(f"Ошибка при обработке тайм-аута для chat_id {chat_id}: {e}", exc_info=True)
    finally:
        ACTIVE_TIMERS.pop(chat_id, None)

def run_orchestrator():
    """
    Основной цикл оркестратора. Потребляет сообщения из Kafka
    и управляет таймерами для обработки.
    """
    consumer = MockKafkaConsumer(KAFKA_TOPIC_NOTIFICATIONS)
    logger.info("Запуск Orchestrator...")
    for message in consumer:
        try:
            data = json.loads(message.value)
            chat_id = data.get("chat_id")
            if not chat_id:
                logger.warning("Получено сообщение без chat_id, пропускаю.")
                continue

            logger.info(f"Получено уведомление для chat_id: {chat_id}")

            SCREENSHOT_BUFFER[chat_id].append(data)

            if chat_id not in ACTIVE_TIMERS:
                logger.info(f"Запуск нового таймера для chat_id: {chat_id}")
                timer = threading.Timer(ORCHESTRATOR_TIMEOUT, process_timeout, args=[chat_id])
                ACTIVE_TIMERS[chat_id] = timer
                timer.start()
            else:
                logger.info(f"Таймер для chat_id: {chat_id} уже активен. Буферизация скриншота.")

        except json.JSONDecodeError:
            logger.error("Не удалось декодировать сообщение из Kafka.", exc_info=True)
        except Exception as e:
            logger.error(f"Произошла непредвиденная ошибка в оркестраторе: {e}", exc_info=True)

if __name__ == "__main__":
    # Этот блок теперь в основном для отладки, т.к. запуск идет из run.py
    setup_logging()
    logger.info("Модуль Orchestrator готов к запуску.")