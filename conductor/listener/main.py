import sys
import os
import logging
import uvicorn
from fastapi import FastAPI, Request, HTTPException

# Настройка пути для импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.abstractions import AbstractListener
from conductor.screenshotter.main import trigger_screenshot

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)

class WebhookListener(AbstractListener):
    """
    Слушатель, который принимает входящие веб-хуки через FastAPI.
    """
    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.app = FastAPI()
        self._configure_routes()

    def _configure_routes(self):
        """Настраивает маршруты для FastAPI-приложения."""
        @self.app.post("/webhook")
        async def receive_webhook(request: Request):
            try:
                data = await request.json()
                chat_id = data.get("chat_id")

                if not chat_id:
                    logger.warning("Получен запрос без chat_id.")
                    raise HTTPException(status_code=400, detail="chat_id is required")

                logger.info(f"Получен веб-хук для chat_id: {chat_id}")
                trigger_screenshot(chat_id)
                return {"status": "ok", "message": f"Screenshot process triggered for chat_id: {chat_id}"}
            except Exception as e:
                logger.error(f"Ошибка при обработке веб-хука: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal Server Error")

        @self.app.get("/")
        def read_root():
            logger.info("Проверка корневого эндпоинта. Listener активен.")
            return {"message": "Conductor Webhook Listener is running."}

    def start(self):
        """
        Запускает веб-сервер uvicorn для приема веб-хуков.
        """
        logger.info(f"Запуск WebhookListener на {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)

# Этот блок позволяет запускать файл напрямую для отладки
if __name__ == "__main__":
    listener = WebhookListener()
    listener.start()