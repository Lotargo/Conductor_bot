import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sentio_engine.core.engine import SentioEngine
from sentio_engine.schemas.sentio_pb2 import Stimulus
from sentio_engine.data.database import Base, EmotionalHistory

# --- Фикстуры для тестов ---

@pytest.fixture(scope="session")
def config_path():
    """Возвращает путь к директории с тестовыми конфигами."""
    # Для тестов лучше использовать отдельные, упрощенные конфиги.
    # Но пока для простоты будем использовать те же, что и в приложении.
    return Path(__file__).resolve().parent.parent / "config"

@pytest.fixture
def db_session():
    """Создает сессию для тестовой БД в памяти."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def engine(config_path, db_session):
    """Создает экземпляр SentioEngine для каждого теста."""
    return SentioEngine(config_path=config_path)

# --- Модульные тесты ---

def test_engine_initialization(engine: SentioEngine):
    """Проверяет, что движок корректно инициализируется."""
    assert engine.state.primary_mood == "преобладает любопытство"
    assert engine.state.emotions["радость"] == pytest.approx(0.1)
    assert "Инициализация системы" in engine.state.cause

def test_process_stimulus_updates_state(engine: SentioEngine, db_session):
    """Проверяет, что стимул корректно обновляет состояние."""
    initial_joy = engine.state.emotions["радость"]

    stimulus = Stimulus()
    stimulus.emotions["радость"] = 0.5

    engine.process_stimulus(stimulus, db=db_session)

    assert engine.state.emotions["радость"] > initial_joy
    assert "радость" in engine.state.cause

def test_process_stimulus_logs_to_db(engine: SentioEngine, db_session):
    """Проверяет, что обработка стимула создает запись в БД."""
    stimulus = Stimulus()
    stimulus.emotions["грусть"] = 0.7

    engine.process_stimulus(stimulus, db=db_session)

    history = db_session.query(EmotionalHistory).all()
    assert len(history) == 1
    assert history[0].emotion == "грусть"
    assert history[0].intensity > 0.7

def test_emotion_decay(engine: SentioEngine):
    """Проверяет, что эмоции со временем затухают."""
    # Устанавливаем высокую интенсивность
    engine.state.emotions["доверие"] = 1.0

    # Вызываем затухание напрямую
    engine._decay_emotions()

    assert engine.state.emotions["доверие"] < 1.0
    # Проверяем, что оно стремится к базовому значению (0.2), а не к нулю
    assert engine.state.emotions["доверие"] > 0.2
