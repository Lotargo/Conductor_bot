import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """
    Настраивает логирование для вывода структурированных JSON-логов.
    Это идеально подходит для систем управления логами, таких как Grafana Loki.
    """
    logger = logging.getLogger()

    # Устанавливаем уровень логирования. INFO - хороший баланс между детализацией и объемом.
    logger.setLevel(logging.INFO)

    # Предотвращаем дублирование обработчиков, если функция вызывается несколько раз
    if logger.hasHandlers():
        logger.handlers.clear()

    # Создаем обработчик, который будет выводить логи в стандартный вывод (консоль)
    log_handler = logging.StreamHandler(sys.stdout)

    # Определяем формат JSON-логов.
    # Эти поля являются стандартными и хорошо распознаются агрегаторами логов.
    # asctime - время, name - имя логгера (модуля), levelname - уровень (INFO, ERROR), message - сообщение.
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )

    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    logging.info("Конфигурация логирования завершена. Логи будут выводиться в формате JSON.")