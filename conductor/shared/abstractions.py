from abc import ABC, abstractmethod

class AbstractListener(ABC):
    """
    Абстрактный базовый класс для всех слушателей (listeners).
    Определяет общий интерфейс для запуска слушателя.
    """
    @abstractmethod
    def start(self):
        """
        Запускает слушателя для приема входящих сообщений/событий.
        """
        pass

class AbstractExecutor(ABC):
    """
    Абстрактный базовый класс для всех исполнителей (executors).
    Определяет общий интерфейс для выполнения действий.
    """
    @abstractmethod
    def start(self):
        """
        Запускает исполнителя для обработки команд.
        """
        pass