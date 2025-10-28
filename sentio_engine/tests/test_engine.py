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
    # Согласно новому emotions.json, "доверие" имеет самую высокую base_intensity (0.2)
    assert engine.state.primary_mood == "преобладает доверие"
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

    # С новой логикой доминантности, где слабейший подавляется,
    # и base_intensity отвращения = 0, доверие (1.0) подавит его до 0.
    # Поэтому результат decay будет чистым, без влияния противоположности.
    assert engine.state.emotions["доверие"] == pytest.approx(0.992)

def test_time_based_decay_synchronization(engine: SentioEngine, db_session):
    """Проверяет, что затухание корректно синхронизируется со временем."""
    import datetime
    from sentio_engine.data.database import EngineState

    engine.state.emotions["радость"] = 1.0
    engine.state.emotions["грусть"] = 0.0 # Убеждаемся, что грусти нет
    engine._synchronize_decay(db=db_session)

    state = db_session.query(EngineState).first()
    assert state is not None
    ten_minutes_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
    state.last_update_timestamp = ten_minutes_ago
    db_session.commit()

    engine._synchronize_decay(db=db_session)

    final_joy = engine.state.emotions["радость"]
    assert final_joy < 0.8
    assert final_joy > engine.emotion_definitions["радость"]["base_intensity"]

def test_dominance_suppresses_weaker_emotion(engine: SentioEngine):
    """Проверяет, что сильная эмоция подавляет слабую противоположность."""
    engine.state.emotions["радость"] = 1.0
    engine.state.emotions["грусть"] = 0.5

    engine._apply_dominance()

    # Радость (1.0) > Грусть (0.5), поэтому Радость остается, а Грусть подавляется.
    # new_sadness = 0.5 - (1.0 * 0.5) = 0.0
    assert engine.state.emotions["радость"] == 1.0
    assert engine.state.emotions["грусть"] == pytest.approx(0.0)

def test_dominance_is_suppressed_by_stronger_emotion(engine: SentioEngine):
    """Проверяет, что слабая эмоция подавляется сильной противоположностью."""
    engine.state.emotions["радость"] = 0.3
    engine.state.emotions["грусть"] = 0.8

    engine._apply_dominance()

    # Грусть (0.8) > Радость (0.3), поэтому Грусть остается, а Радость подавляется.
    # new_joy = 0.3 - (0.8 * 0.5) = -0.1 -> 0.0
    assert engine.state.emotions["радость"] == pytest.approx(0.0)
    assert engine.state.emotions["грусть"] == pytest.approx(0.8)

# --- Тесты для Комплексных Состояний ---
import datetime

class TestComplexStates:
    def _create_history(self, db_session, emotion, intensity, hours_ago, cause="test"):
        """Хелпер для создания записей в истории."""
        timestamp = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_ago)
        entry = EmotionalHistory(
            emotion=emotion,
            intensity=intensity,
            cause=cause,
            timestamp=timestamp
        )
        db_session.add(entry)
        db_session.commit()

    def test_no_complex_state_on_short_history(self, engine: SentioEngine, db_session):
        """Проверяет, что состояние не определяется, если история слишком коротка."""
        # Симулируем высокую грусть, но только за последние 12 часов
        for i in range(12):
            self._create_history(db_session, "грусть", 0.8, hours_ago=i)

        states = engine._evaluate_complex_states(db_session)
        assert "депрессивное состояние" not in states

    def test_detects_depression_state(self, engine: SentioEngine, db_session):
        """Проверяет корректное определение 'депрессивного состояния'."""
        # Согласно feelings.json, нужно 2 недели (336 часов)
        # Условие: грусть >= 0.7, радость <= 0.2
        required_hours = engine.feelings_definitions["депрессивное состояние"]["required_duration_hours"]

        # Симулируем 350 часов (с запасом)符合условий
        for i in range(required_hours + 20):
            self._create_history(db_session, "грусть", 0.8, hours_ago=i)
            self._create_history(db_session, "радость", 0.1, hours_ago=i)

        states = engine._evaluate_complex_states(db_session)
        assert "депрессивное состояние" in states

    def test_depression_state_not_detected_if_joy_is_present(self, engine: SentioEngine, db_session):
        """Проверяет, что состояние не определяется, если радость периодически высокая."""
        required_hours = engine.feelings_definitions["депрессивное состояние"]["required_duration_hours"]

        for i in range(required_hours + 20):
            self._create_history(db_session, "грусть", 0.8, hours_ago=i)
            # Каждые 10 часов происходит вспышка радости, нарушающая условие
            joy_intensity = 0.5 if i % 10 == 0 else 0.1
            self._create_history(db_session, "радость", joy_intensity, hours_ago=i)

        states = engine._evaluate_complex_states(db_session)
        assert "депрессивное состояние" not in states
