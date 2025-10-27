# --- Ступень 1: Сборка зависимостей ---
FROM python:3.11-slim as builder

# Устанавливаем Poetry
RUN pip install poetry

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы Poetry
COPY pyproject.toml poetry.lock* ./

# Устанавливаем зависимости в виртуальное окружение,
# --no-root, так как исходный код еще не скопирован
RUN poetry install --no-root --without dev

# --- Ступень 2: Финальный образ ---
FROM python:3.11-slim

WORKDIR /app

# Копируем виртуальное окружение со всеми зависимостями из ступени сборки
COPY --from=builder /root/.cache/pypoetry/virtualenvs/ /root/.cache/pypoetry/virtualenvs/

# Копируем исходный код нашего приложения
COPY sentio_engine/ ./sentio_engine/

# Указываем Python-интерпретатор из нашего виртуального окружения
# Имя virtualenv может меняться, поэтому используем wildcard
ENV PATH="/root/.cache/pypoetry/virtualenvs/sentio-engine-*-py3.11/bin:$PATH"

# Открываем порт
EXPOSE 8000

# Запускаем приложение через Gunicorn для production
# Gunicorn будет управлять Uvicorn воркерами
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "sentio_engine.api.main:app"]
