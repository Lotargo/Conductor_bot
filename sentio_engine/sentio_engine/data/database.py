from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime

# Получаем URL базы данных из переменной окружения, по умолчанию используем локальный файл SQLite
DATABASE_URL = "sqlite:///./sentio_engine.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Модели Таблиц ---

class EmotionalHistory(Base):
    """Логирование изменений эмоционального состояния с течением времени."""
    __tablename__ = "emotional_history"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    emotion = Column(String, index=True)
    intensity = Column(Float)
    cause = Column(String)

class EmotionalMemory(Base):
    """Хранение "триггеров" - ассоциаций между стимулами и сильными эмоциональными реакциями."""
    __tablename__ = "emotional_memory"
    id = Column(Integer, primary_key=True, index=True)
    trigger_stimulus = Column(String, unique=True, index=True) # Описание стимула
    associated_emotion = Column(String) # Эмоция, которая была вызвана
    intensity_modifier = Column(Float) # Насколько сильно этот триггер меняет эмоцию

class RelationshipState(Base):
    """Хранение метрик отношений с конкретным пользователем или сессией."""
    __tablename__ = "relationship_state"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    familiarity = Column(Float, default=0.0) # Насколько ИИ "знаком" с пользователем
    intimacy = Column(Float, default=0.0) # Уровень близости/доверия
    trust = Column(Float, default=0.5) # Уровень доверия

class EngineState(Base):
    """Хранит мета-состояние самого движка."""
    __tablename__ = "engine_state"
    id = Column(Integer, primary_key=True)
    last_update_timestamp = Column(DateTime, nullable=False)

def create_db_and_tables():
    """Создает все таблицы в базе данных."""
    Base.metadata.create_all(bind=engine, checkfirst=True)

# Удобная функция для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
