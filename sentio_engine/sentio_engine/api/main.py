from fastapi import FastAPI, Request, Response, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import hashlib

from sentio_engine.core.engine import SentioEngine
from sentio_engine.schemas.sentio_pb2 import Stimulus, Report
from contextlib import asynccontextmanager
from sentio_engine.data.database import create_db_and_tables, get_db
from sentio_engine.cache.redis_client import get_redis_client

# --- DB Initialization ---
# This is executed once when the module is first imported by Gunicorn's master process.
create_db_and_tables()

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом приложения."""
    yield
    print("Приложение остановлено.")

# --- Инициализация Приложения и Движка ---
app = FastAPI(title="Sentio Engine API", lifespan=lifespan)

config_path = Path(__file__).resolve().parent.parent.parent / "config"
engine = SentioEngine(config_path=config_path)

# --- API Эндпоинты ---
@app.post("/stimulus", status_code=204, summary="Применить стимул к движку")
async def apply_stimulus(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    stimulus = Stimulus()
    try:
        stimulus.ParseFromString(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Ошибка парсинга Protobuf-сообщения.")
    engine.process_stimulus(stimulus, db=db)
    return Response(status_code=204)

@app.post("/process_and_report", response_class=Response, summary="Обработать стимул и вернуть отчет с кэшированием")
async def process_and_report(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    stimulus = Stimulus()
    try:
        stimulus.ParseFromString(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Ошибка парсинга Protobuf-сообщения.")

    redis_client = get_redis_client()
    stimulus_hash = hashlib.sha256(body).hexdigest()
    cached_report_str = redis_client.get(stimulus_hash)

    if cached_report_str:
        return Response(content=cached_report_str, media_type="application/protobuf")

    engine.process_stimulus(stimulus, db=db)
    report = engine.get_report()
    serialized_report = report.SerializeToString()

    redis_client.setex(stimulus_hash, 3600, serialized_report)

    return Response(content=serialized_report, media_type="application/protobuf")

@app.get("/report", response_class=Response, summary="Получить отчет о состоянии")
def get_engine_report():
    report = engine.get_report()
    serialized_report = report.SerializeToString()
    return Response(content=serialized_report, media_type="application/protobuf")

# --- Запуск Сервера (для локальной разработки) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
