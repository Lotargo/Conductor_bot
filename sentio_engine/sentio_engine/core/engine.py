import json
import numpy as np
from pathlib import Path
from sqlalchemy.orm import Session
from sentio_engine.schemas.sentio_pb2 import EmotionalState, Stimulus, Report
from sentio_engine.data.database import SessionLocal, EmotionalHistory

class SentioEngine:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._load_configuration()
        self.state = EmotionalState()
        self._initialize_state()

    def _load_configuration(self):
        """Загружает конфигурацию личности из JSON-файлов."""
        with open(self.config_path / "emotions.json", "r", encoding="utf-8") as f:
            self.emotion_definitions = json.load(f)["definitions"]
        with open(self.config_path / "drives.json", "r", encoding="utf-8") as f:
            self.drive_definitions = json.load(f)["definitions"]

    def _initialize_state(self):
        """Инициализирует начальное эмоциональное состояние."""
        for emotion, params in self.emotion_definitions.items():
            self.state.emotions[emotion] = params["base_intensity"]
        self._update_primary_mood()
        self.state.cause = "Инициализация системы."

    def _update_primary_mood(self):
        """Определяет доминирующее настроение на основе текущих эмоций."""
        if not self.state.emotions:
            self.primary_mood = "нейтральное"
            return

        primary_emotion = max(self.state.emotions, key=self.state.emotions.get)
        self.state.primary_mood = f"преобладает {primary_emotion}"

    def process_stimulus(self, stimulus: Stimulus, db: Session):
        """Обрабатывает входящий стимул, обновляет состояние и логирует изменения."""
        cause_text = "Неизвестный стимул"
        if stimulus.emotions:
            top_stimulus = max(stimulus.emotions, key=stimulus.emotions.get)
            cause_text = f"Реакция на стимул: {top_stimulus}"

        self.state.cause = cause_text

        for emotion, intensity in stimulus.emotions.items():
            if emotion in self.state.emotions:
                self.state.emotions[emotion] += intensity
                self.state.emotions[emotion] = max(0.0, min(1.0, self.state.emotions[emotion]))

                # Логируем изменение в БД
                history_entry = EmotionalHistory(
                    emotion=emotion,
                    intensity=self.state.emotions[emotion],
                    cause=cause_text
                )
                db.add(history_entry)

        db.commit()
        self._update_primary_mood()
        self._decay_emotions()

    def _decay_emotions(self):
        """Моделирует постепенное затухание эмоций со временем."""
        for emotion, intensity in self.state.emotions.items():
            decay_rate = self.emotion_definitions.get(emotion, {}).get("decay_rate", 0.99)
            base_intensity = self.emotion_definitions.get(emotion, {}).get("base_intensity", 0.0)

            # Эмоция стремится вернуться к своему базовому уровню
            if intensity > base_intensity:
                self.state.emotions[emotion] = max(base_intensity, intensity * decay_rate)
            else:
                self.state.emotions[emotion] = min(base_intensity, intensity / decay_rate if decay_rate != 0 else 0)

    def get_report(self) -> Report:
        """Возвращает полный отчет о текущем состоянии."""
        report = Report()
        report.emotional_state.CopyFrom(self.state)
        return report

# Пример использования (для тестирования)
if __name__ == '__main__':
    from sentio_engine.data.database import create_db_and_tables, SessionLocal

    # 1. Создаем таблицы в БД
    create_db_and_tables()

    # 2. Создаем сессию БД
    db_session = SessionLocal()

    # 3. Инициализируем движок
    config_dir = Path(__file__).parent.parent / "config"
    engine = SentioEngine(config_path=config_dir)

    print("--- Начальное состояние ---")
    print(engine.get_report())

    # 4. Симулируем стимул
    stimulus_data = Stimulus()
    stimulus_data.emotions["радость"] = 0.5
    stimulus_data.emotions["доверие"] = 0.3

    print("\n--- Обработка стимула: радость и доверие ---")
    engine.process_stimulus(stimulus_data, db=db_session)
    print(engine.get_report())

    # 5. Проверяем, что данные записались в БД
    history = db_session.query(EmotionalHistory).all()
    print(f"\n--- Записи в EmotionalHistory: {len(history)} ---")
    for entry in history:
        print(f"  - {entry.timestamp}: {entry.emotion} = {entry.intensity:.2f} (Причина: {entry.cause})")

    db_session.close()
