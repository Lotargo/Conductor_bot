# --- Ступень 1: Сборка зависимостей ---
FROM python:3.11-slim as builder

# Устанавливаем Poetry
RUN pip install poetry

# Устанавливаем рабочую директорию
WORKDIR /app

# Настраиваем Poetry для создания virtualenv в папке проекта
RUN poetry config virtualenvs.in-project true

# Копируем файлы Poetry
COPY pyproject.toml poetry.lock* ./

# Устанавливаем зависимости
RUN poetry install --no-root --without dev

# --- Ступень 2: Финальный образ ---
FROM python:3.11-slim

WORKDIR /app

# Копируем виртуальное окружение со всеми зависимостями из ступени сборки
COPY --from=builder /app/.venv/ ./.venv/

# Копируем исходный код нашего приложения
COPY sentio_engine/ ./sentio_engine/

# Указываем Python-интерпретатор из нашего виртуального окружения
ENV PATH="/app/.venv/bin:$PATH"

# Открываем порт
EXPOSE 8000

# Запускаем приложение через Gunicorn для production
# Gunicorn будет управлять Uvicorn воркерами
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "sentio_engine.api.main:app"]
