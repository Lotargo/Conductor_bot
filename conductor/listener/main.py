import sys
import os
import logging
from fastapi import FastAPI, Request, HTTPException

# Настройка пути для импорта из родительской директории
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.screenshotter.main import trigger_screenshot

# Получаем экземпляр логгера
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Принимает уведомление по веб-хуку (например, от WhatsApp) и
    запускает процесс создания скриншота.
    """
    try:
        data = await request.json()
        chat_id = data.get("chat_id")

        if not chat_id:
            logger.warning("Получен запрос без chat_id.")
            raise HTTPException(status_code=400, detail="chat_id is required")

        logger.info(f"Получен веб-хук для chat_id: {chat_id}")

        # Запускаем создание скриншота
        trigger_screenshot(chat_id)

        return {"status": "ok", "message": f"Screenshot process triggered for chat_id: {chat_id}"}
    except Exception as e:
        logger.error(f"Ошибка при обработке веб-хука: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/")
def read_root():
    """
    Корневой эндпоинт для проверки работоспособности сервиса.
    """
    logger.info("Проверка корневого эндпоинта. Listener активен.")
    return {"message": "Conductor Listener is running."}