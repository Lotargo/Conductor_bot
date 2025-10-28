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
