import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sentio_engine.api.main import app, get_db
from sentio_engine.data.database import Base

# --- Настройка тестовой БД ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем таблицы в тестовой БД
Base.metadata.create_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Создает новую сессию БД для каждого теста и откатывает изменения после."""
    connection = engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    yield db

    db.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Создает тестовый клиент, который использует тестовую сессию БД."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]


# --- Тесты для эндпоинта /process_agent_text ---

def test_process_agent_text_success(client):
    """Тест: корректный текст с тегом обновляет состояние."""
    text_payload = {
        "text": "[SENTIO_EMO_STATE]\n" '{"радость": 0.8}\n' "[/SENTIO_EMO_STATE]"
    }
    response = client.post("/process_agent_text", json=text_payload)
    assert response.status_code == 204

# --- Тест для эндпоинта /report ---
import datetime
from sentio_engine.data.database import EmotionalHistory
from sentio_engine.schemas.sentio_pb2 import Report
from sentio_engine.api.main import engine as api_engine # импортируем инстанс движка из API

def test_report_includes_complex_states(client, db_session):
    """
    Тест: Проверяет, что эндпоинт /report корректно возвращает комплексные состояния.
    """
    # 1. Создаем историю, достаточную для активации состояния
    required_hours = api_engine.feelings_definitions["депрессивное состояние"]["required_duration_hours"]
    for i in range(required_hours + 5):
        # Создаем запись для грусти
        ts_sad = datetime.datetime.utcnow() - datetime.timedelta(hours=i)
        entry_sad = EmotionalHistory(emotion="грусть", intensity=0.9, cause="test", timestamp=ts_sad)
        db_session.add(entry_sad)

        # Создаем запись для радости
        ts_joy = datetime.datetime.utcnow() - datetime.timedelta(hours=i)
        entry_joy = EmotionalHistory(emotion="радость", intensity=0.1, cause="test", timestamp=ts_joy)
        db_session.add(entry_joy)
    db_session.commit()

    # 2. Делаем GET-запрос
    response = client.get("/report")
    assert response.status_code == 200

    # 3. Парсим Protobuf-ответ
    report = Report()
    report.ParseFromString(response.content)

    # 4. Проверяем наличие комплексного состояния
    assert "депрессивное состояние" in report.complex_states

def test_process_agent_text_no_tag(client):
    """Тест: текст без тега не должен вызывать ошибок."""
    text_payload = {"text": "Просто текст без какого-либо тега."}
    response = client.post("/process_agent_text", json=text_payload)
    assert response.status_code == 204

def test_process_agent_text_invalid_json(client):
    """Тест: текст с невалидным JSON в теге."""
    text_payload = {
        "text": "[SENTIO_EMO_STATE]{'невалидный': json, }[/SENTIO_EMO_STATE]"
    }
    response = client.post("/process_agent_text", json=text_payload)
    assert response.status_code == 204

def test_process_agent_text_empty_json(client):
    """Тест: текст с пустым JSON в теге."""
    text_payload = {
        "text": "[SENTIO_EMO_STATE]{}[/SENTIO_EMO_STATE]"
    }
    response = client.post("/process_agent_text", json=text_payload)
    assert response.status_code == 204
