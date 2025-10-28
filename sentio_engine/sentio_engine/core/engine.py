import json
import numpy as np
from pathlib import Path
from sqlalchemy.orm import Session
import datetime

from sentio_engine.schemas.sentio_pb2 import EmotionalState, Stimulus, Report
from sentio_engine.data.database import EmotionalHistory, EngineState

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
        with open(self.config_path / "engine_settings.json", "r", encoding="utf-8") as f:
            self.engine_settings = json.load(f)
        with open(self.config_path / "feelings.json", "r", encoding="utf-8") as f:
            self.feelings_definitions = json.load(f)

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

    def _synchronize_decay(self, db: Session):
        """Синхронизирует затухание эмоций с реальным временем."""
        now = datetime.datetime.utcnow()
        engine_state = db.query(EngineState).first()

        if not engine_state:
            # Первый запуск, инициализируем состояние
            engine_state = EngineState(last_update_timestamp=now)
            db.add(engine_state)
            db.commit()
            return

        time_elapsed = now - engine_state.last_update_timestamp
        tick_seconds = self.engine_settings.get("simulation_tick_seconds", 60)

        if tick_seconds <= 0:
             return # Избегаем деления на ноль

        steps_to_simulate = int(time_elapsed.total_seconds() / tick_seconds)

        if steps_to_simulate > 0:
            for _ in range(steps_to_simulate):
                self._decay_emotions()

            engine_state.last_update_timestamp = now
            db.commit()

    def process_stimulus(self, stimulus: Stimulus, db: Session):
        """Обрабатывает входящий стимул, обновляет состояние и логирует изменения."""
        self._synchronize_decay(db)

        cause_text = "Неизвестный стимул"
        if stimulus.emotions:
            top_stimulus = max(stimulus.emotions, key=stimulus.emotions.get)
            cause_text = f"Реакция на стимул: {top_stimulus}"

        self.state.cause = cause_text

        for emotion, intensity in stimulus.emotions.items():
            if emotion in self.state.emotions:
                self.state.emotions[emotion] += intensity
                self.state.emotions[emotion] = max(0.0, min(1.0, self.state.emotions[emotion]))

                history_entry = EmotionalHistory(
                    emotion=emotion,
                    intensity=self.state.emotions[emotion],
                    cause=cause_text
                )
                db.add(history_entry)

        # Применяем доминантность до коммита, чтобы в БД попало итоговое состояние
        self._apply_dominance()
        db.commit()
        self._update_primary_mood()

    def _apply_dominance(self):
        """Применяет эффект доминантности, где более сильная эмоция в паре подавляет более слабую."""
        dominance_factor = self.engine_settings.get("dominance_factor", 0.5)
        processed_emotions = set()

        for emotion, intensity in self.state.emotions.items():
            if emotion in processed_emotions:
                continue

            definition = self.emotion_definitions.get(emotion, {})
            opposite_emotion = definition.get("opposite")

            if not opposite_emotion or opposite_emotion not in self.state.emotions:
                continue

            opposite_intensity = self.state.emotions[opposite_emotion]

            # Определяем, какая эмоция доминирует
            if intensity > opposite_intensity:
                # Текущая эмоция подавляет противоположную
                suppression = intensity * dominance_factor
                self.state.emotions[opposite_emotion] = max(0.0, opposite_intensity - suppression)
            elif opposite_intensity > intensity:
                # Противоположная эмоция подавляет текущую
                suppression = opposite_intensity * dominance_factor
                self.state.emotions[emotion] = max(0.0, intensity - suppression)

            processed_emotions.add(emotion)
            processed_emotions.add(opposite_emotion)


    def _decay_emotions(self):
        """Моделирует постепенное затухание эмоций со временем."""
        # Создаем копию словаря для безопасной итерации
        emotions_snapshot = dict(self.state.emotions)

        for emotion, intensity in emotions_snapshot.items():
            decay_rate = self.emotion_definitions.get(emotion, {}).get("decay_rate", 0.99)
            base_intensity = self.emotion_definitions.get(emotion, {}).get("base_intensity", 0.0)

            new_intensity = base_intensity + (intensity - base_intensity) * decay_rate
            self.state.emotions[emotion] = new_intensity

        self._apply_dominance()

    def _evaluate_complex_states(self, db: Session) -> list[str]:
        """Анализирует историю эмоций для выявления сложных состояний (чувств)."""
        active_states = []
        now = datetime.datetime.utcnow()

        for state_name, definition in self.feelings_definitions.items():
            duration_hours = definition.get("required_duration_hours", 24 * 14)
            start_time = now - datetime.timedelta(hours=duration_hours)

            is_state_active = True

            # Предварительная проверка: есть ли в окне хоть какие-то записи?
            # Если нет, то состояние точно не активно.
            has_any_record_in_window = db.query(EmotionalHistory).filter(EmotionalHistory.timestamp >= start_time).first() is not None
            if not has_any_record_in_window:
                is_state_active = False
            else:
                for condition in definition.get("conditions", []):
                    emotion = condition["emotion"]
                    threshold = condition["threshold"]
                    operator = condition["operator"]

                    # 1. Проверка на НАРУШЕНИЯ: ищем записи, которые НЕ соответствуют условию.
                    q_violating = db.query(EmotionalHistory).filter(
                        EmotionalHistory.timestamp >= start_time,
                        EmotionalHistory.emotion == emotion
                    )
                    if operator == ">=":
                        q_violating = q_violating.filter(EmotionalHistory.intensity < threshold)
                    elif operator == "<=":
                        q_violating = q_violating.filter(EmotionalHistory.intensity > threshold)

                    if db.query(q_violating.exists()).scalar():
                        is_state_active = False
                        break # Нарушение найдено, прекращаем проверку этого состояния.

                    # 2. Проверка на НАЛИЧИЕ: убеждаемся, что для данной эмоции есть хоть одна запись в периоде.
                    # Если записей нет, мы не можем утверждать, что условие выполнялось.
                    q_presence = db.query(EmotionalHistory).filter(
                        EmotionalHistory.timestamp >= start_time,
                        EmotionalHistory.emotion == emotion
                    )
                    if not db.query(q_presence.exists()).scalar():
                        is_state_active = False
                        break # Нет данных для этой эмоции, прекращаем проверку.

            if is_state_active:
                active_states.append(state_name)

        return active_states

    def get_report(self, db: Session) -> Report:
        """Синхронизирует состояние и возвращает полный отчет."""
        self._synchronize_decay(db)
        report = Report()
        report.emotional_state.CopyFrom(self.state)

        # Анализируем и добавляем комплексные состояния
        active_complex_states = self._evaluate_complex_states(db)
        report.complex_states.extend(active_complex_states)

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
