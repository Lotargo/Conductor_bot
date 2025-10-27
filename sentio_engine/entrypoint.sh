#!/bin/sh
set -e

# Активируем виртуальное окружение.
# Это самый надежный способ получить доступ к правильному python
# и установленным зависимостям.
. /app/.venv/bin/activate

echo "Entrypoint: Инициализация базы данных..."
# Теперь мы можем напрямую вызывать python, и это будет
# интерпретатор из .venv.
python -c "from sentio_engine.data.database import create_db_and_tables; create_db_and_tables()"
echo "Entrypoint: База данных готова."

# Передаем управление основной команде контейнера (CMD из Dockerfile).
exec "$@"
