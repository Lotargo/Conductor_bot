from fastapi import FastAPI, Request, Response, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import hashlib

from sentio_engine.core.engine import SentioEngine
from sentio_engine.schemas.sentio_pb2 import Stimulus, Report
from contextlib import asynccontextmanager
from sentio_engine.data.database import create_db_and_tables, get_db
from sentio_engine.cache.redis_client import get_redis_client

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом приложения."""
    print("Запуск приложения...")
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


# --- Эндпоинт для обработки текста от Агента ---
import re
import json
from pydantic import BaseModel

class AgentText(BaseModel):
    text: str

def _parse_emotions_from_text(text: str) -> dict | None:
    """Извлекает JSON-объект с эмоциями из специального тега в тексте."""
    match = re.search(r"\[SENTIO_EMO_STATE\](.*?)\[/SENTIO_EMO_STATE\]", text, re.DOTALL)
    if not match:
        return None

    json_str = match.group(1).strip()
    try:
        emotions = json.loads(json_str)
        if isinstance(emotions, dict):
            return emotions
    except json.JSONDecodeError:
        return None
    return None

@app.post("/process_agent_text", status_code=204, summary="Обработать текст от агента и извлечь эмоции")
async def process_agent_text(payload: AgentText, db: Session = Depends(get_db)):
    """
    Этот эндпоинт ищет в тексте специальный блок [SENTIO_EMO_STATE]...[/SENTIO_EMO_STATE]
    и использует найденный в нем JSON для обновления эмоционального состояния.
    """
    emotions_to_process = _parse_emotions_from_text(payload.text)

    if emotions_to_process:
        stimulus = Stimulus()
        for emotion, intensity in emotions_to_process.items():
            if isinstance(intensity, (int, float)):
                stimulus.emotions[emotion] = float(intensity)

        if stimulus.emotions:
            engine.process_stimulus(stimulus, db=db)

    return Response(status_code=204)


# --- Запуск Сервера (для локальной разработки) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
