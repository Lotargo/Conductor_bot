import pytest
from pathlib import Path
from unittest.mock import MagicMock

from sentio_engine.core.engine import SentioEngine
from sentio_engine.schemas.sentio_pb2 import Stimulus

@pytest.fixture
def config_path():
    """Возвращает путь к директории с конфигурационными файлами."""
    return Path(__file__).parent.parent / "config"

@pytest.fixture
def engine(config_path):
    """Фикстура для создания экземпляра SentioEngine."""
    return SentioEngine(config_path=config_path)

def test_personality_neuroticism_amplifies_fear(engine):
    """
    Тест: Личность с высоким нейротизмом должна сильнее реагировать на страх.
    """
    # Arrange: Устанавливаем высокий уровень нейротизма
    engine.belief_system["neuroticism"]["value"] = 1.0
    stimulus = Stimulus()
    stimulus.emotions["страх"] = 0.5

    initial_fear_intensity = engine.state.emotions["страх"]

    # Act: Обрабатываем стимул
    mock_db_session = MagicMock()
    engine.process_stimulus(stimulus, db=mock_db_session)

    # Assert: Проверяем, что интенсивность страха увеличилась значительно
    final_fear_intensity = engine.state.emotions["страх"]
    increase = final_fear_intensity - initial_fear_intensity

    # Ожидаемый модификатор: 1 + (1.0 - 0.5) * (1.5 - 1) = 1.25
    # Ожидаемое увеличение: 0.5 * 1.25 = 0.625
    assert increase == pytest.approx(0.625)

def test_personality_agreeableness_dampens_anger(engine):
    """
    Тест: Личность с высокой доброжелательностью должна слабее реагировать на злость.
    """
    # Arrange: Устанавливаем высокий уровень доброжелательности
    engine.belief_system["agreeableness"]["value"] = 1.0
    stimulus = Stimulus()
    stimulus.emotions["злость"] = 0.5

    initial_anger_intensity = engine.state.emotions["злость"]

    # Act: Обрабатываем стимул
    mock_db_session = MagicMock()
    engine.process_stimulus(stimulus, db=mock_db_session)

    # Assert: Проверяем, что интенсивность злости увеличилась незначительно
    final_anger_intensity = engine.state.emotions["злость"]
    increase = final_anger_intensity - initial_anger_intensity

    # Ожидаемый модификатор: 1 + (1.0 - 0.5) * (0.6 - 1) = 0.8
    # Ожидаемое увеличение: 0.5 * 0.8 = 0.4
    assert increase == pytest.approx(0.4)

def test_personality_neutral_no_effect(engine):
    """
    Тест: Личность со средними показателями (0.5) не должна изменять реакцию.
    """
    # Arrange: Все черты личности установлены в 0.5 по умолчанию
    stimulus = Stimulus()
    stimulus.emotions["радость"] = 0.5

    initial_joy_intensity = engine.state.emotions["радость"]

    # Act: Обрабатываем стимул
    mock_db_session = MagicMock()
    engine.process_stimulus(stimulus, db=mock_db_session)

    # Assert: Проверяем, что увеличение интенсивности равно исходному
    final_joy_intensity = engine.state.emotions["радость"]
    increase = final_joy_intensity - initial_joy_intensity

    # Ожидаемый модификатор: ~1.0
    # Ожидаемое увеличение: 0.5 * 1.0 = 0.5
    assert increase == pytest.approx(0.5)
