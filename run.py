import threading
import time
import sys
import os
import logging

# Убедимся, что директория 'conductor' находится в Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from conductor.logging_config import setup_logging
from conductor.config import TELEGRAM_BOT_TOKEN

# Импортируем классы, а не функции
from conductor.listener.main import WebhookListener
from conductor.listener.telegram_listener import TelegramListener
from conductor.orchestrator.main import run_orchestrator
from conductor.decision_engine.main import run_decision_engine
from conductor.executor.main import ActionExecutor

# Настраиваем логирование при старте модуля
setup_logging()
logger = logging.getLogger(__name__)

def run_webhook_listener():
    """Инициализирует и запускает WebhookListener."""
    listener = WebhookListener(host="0.0.0.0", port=8000)
    listener.start()

def run_telegram_listener():
    """Инициализирует и запускает TelegramListener, если токен предоставлен."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN':
        logger.warning("Токен для Telegram-бота не настроен в config.py. TelegramListener не будет запущен.")
        return

    logger.info("Запуск TelegramListener...")
    listener = TelegramListener(bot_token=TELEGRAM_BOT_TOKEN)
    listener.start()

def run_action_executor():
    """Инициализирует и запускает ActionExecutor."""
    executor = ActionExecutor()
    executor.start()

def main():
    """
    Запускает все модули Conductor одновременно в отдельных потоках.
    """
    logger.info("--- Запуск Conductor AI Assistant ---")

    # Обновляем цели для запуска классов
    targets = {
        "webhook_listener": run_webhook_listener,
        "telegram_listener": run_telegram_listener, # Добавляем новый листенер
        "orchestrator": run_orchestrator,
        "decision_engine": run_decision_engine,
        "executor": run_action_executor, # Используем новую функцию-обертку
    }

    threads = []

    # Создаем и запускаем поток для каждого модуля
    for name, target_func in targets.items():
        # Пропускаем запуск Telegram-листенера, если функция-обертка ничего не делает
        if name == "telegram_listener" and (not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN'):
            continue

        thread = threading.Thread(target=target_func, name=name, daemon=True)
        threads.append(thread)
        logger.info(f"Запуск модуля '{name}' в новом потоке.")
        thread.start()
        time.sleep(1)

    logger.info("--- Все модули запущены. Нажмите Ctrl+C для остановки. ---")
    
    try:
        # Поддерживаем главный поток активным
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("--- Завершение работы Conductor AI Assistant ---")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Критическая ошибка в главном потоке: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()