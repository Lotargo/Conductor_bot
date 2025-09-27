import json
import sys
import os
import logging

# Настройка пути для импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.mocks import MockKafkaConsumer, MockKafkaProducer, MockMagicProxy
from conductor.config import KAFKA_TOPIC_DECISIONS, KAFKA_TOPIC_ACTIONS

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)

def run_decision_engine():
    """
    Основной цикл для механизма принятия решений. Потребляет запросы из Kafka,
    использует Magic Proxy для принятия решения и отправляет результирующее
    действие в топик для исполнения.
    """
    consumer = MockKafkaConsumer(KAFKA_TOPIC_DECISIONS)
    producer = MockKafkaProducer()
    magic_proxy = MockMagicProxy()

    logger.info("Запуск Decision Engine...")
    for message in consumer:
        try:
            request_data = json.loads(message.value)
            chat_id = request_data.get("chat_id")
            persona_manifest = request_data.get("persona_manifest")
            rag_context = request_data.get("rag_context")
            screenshots = request_data.get("screenshots")

            if not all([chat_id, persona_manifest, rag_context, screenshots is not None]):
                logger.warning("Получен неполный запрос на принятие решения, пропускаю.")
                continue

            logger.info(f"Обработка запроса на принятие решения для chat_id: {chat_id}")

            # Получаем решение от Magic Proxy
            action_command = magic_proxy.decide(
                persona_manifest=persona_manifest,
                rag_context=rag_context,
                screenshots=screenshots
            )

            # Добавляем chat_id в итоговую команду
            action_command["chat_id"] = chat_id

            # Отправляем команду в топик для исполнения
            producer.send(KAFKA_TOPIC_ACTIONS, value=json.dumps(action_command))
            producer.flush()

            logger.info(f"Команда на исполнение для chat_id: {chat_id} отправлена в Kafka.")

        except json.JSONDecodeError:
            logger.error("Не удалось декодировать сообщение из Kafka.", exc_info=True)
        except Exception as e:
            logger.error(f"Произошла непредвиденная ошибка в Decision Engine: {e}", exc_info=True)

if __name__ == "__main__":
    # Этот блок теперь в основном для отладки
    setup_logging()
    logger.info("Модуль Decision Engine готов к запуску.")