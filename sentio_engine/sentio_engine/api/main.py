from fastapi import FastAPI, Request, Response, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path

from sentio_engine.core.engine import SentioEngine
from sentio_engine.schemas.sentio_pb2 import Stimulus, Report
from contextlib import asynccontextmanager
from sentio_engine.data.database import create_db_and_tables, get_db

# --- Lifespan Manager ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом приложения."""
    # Код здесь выполняется перед запуском приложения
    print("Создание таблиц в базе данных...")
    create_db_and_tables()
    yield
    # Код здесь выполняется после остановки приложения
    print("Приложение остановлено.")

# --- Инициализация Приложения и Движка ---

app = FastAPI(title="Sentio Engine API", lifespan=lifespan)

# Создаем движок как синглтон.
config_path = Path(__file__).resolve().parent.parent.parent / "config"
engine = SentioEngine(config_path=config_path)

# --- API Эндпоинты ---

@app.post("/stimulus", status_code=204, summary="Применить стимул к движку")
async def apply_stimulus(request: Request, db: Session = Depends(get_db)):
    """
    Принимает бинарный Protobuf-объект `Stimulus`.
    Обрабатывает его и обновляет внутреннее состояние движка.
    """
    body = await request.body()
    stimulus = Stimulus()
    try:
        stimulus.ParseFromString(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Ошибка парсинга Protobuf-сообщения.")

    engine.process_stimulus(stimulus, db=db)
    # Возвращаем 204 No Content, так как ответ не несет полезной нагрузки.
    return Response(status_code=204)

@app.get("/report", response_class=Response, summary="Получить отчет о состоянии")
def get_engine_report():
    """
    Возвращает полный отчет о текущем состоянии движка
    в виде бинарного Protobuf-объекта `Report`.
    """
    report = engine.get_report()
    serialized_report = report.SerializeToString()
    return Response(content=serialized_report, media_type="application/protobuf")

# --- Запуск Сервера (для локальной разработки) ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
