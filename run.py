import threading
import uvicorn
import time
import sys
import os
import logging

# Убедимся, что директория 'conductor' находится в Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from conductor.logging_config import setup_logging
from conductor.listener.main import app as fastapi_app
from conductor.orchestrator.main import run_orchestrator
from conductor.decision_engine.main import run_decision_engine
from conductor.executor.main import run_executor

# Настраиваем логирование при старте модуля
setup_logging()
logger = logging.getLogger(__name__)

def run_fastapi():
    """Запускает FastAPI-приложение listener с помощью uvicorn."""
    logger.info("Запуск Listener (FastAPI)...")
    # Уменьшаем уровень детализации логов uvicorn, чтобы не засорять вывод
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="warning")

def main():
    """
    Запускает все модули Conductor одновременно в отдельных потоках.
    """
    logger.info("--- Запуск Conductor AI Assistant ---")

    # Определяем целевые функции для каждого модуля
    targets = {
        "listener": run_fastapi,
        "orchestrator": run_orchestrator,
        "decision_engine": run_decision_engine,
        "executor": run_executor,
    }

    threads = []

    # Создаем и запускаем поток для каждого модуля
    for name, target_func in targets.items():
        thread = threading.Thread(target=target_func, name=name, daemon=True)
        threads.append(thread)
        logger.info(f"Запуск модуля '{name}' в новом потоке.")
        thread.start()
        time.sleep(1)  # Небольшая задержка для более читаемых логов

    logger.info("--- Все модули запущены. Нажмите Ctrl+C для остановки. ---")
    
    try:
        # Поддерживаем главный поток активным, чтобы daemon-потоки могли работать
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("--- Завершение работы Conductor AI Assistant ---")
        # Потоки являются daemon, поэтому они завершатся вместе с главным потоком.
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Критическая ошибка в главном потоке: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()