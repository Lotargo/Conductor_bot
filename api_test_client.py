import requests
from sentio_engine.schemas.sentio_pb2 import Stimulus, Report

BASE_URL = "http://127.0.0.1:8000"

def test_get_report():
    """Тестирует эндпоинт /report."""
    try:
        response = requests.get(f"{BASE_URL}/report")
        response.raise_for_status()

        report = Report()
        report.ParseFromString(response.content)

        print("--- Получен отчет (начальное состояние) ---")
        print(report)
        return True
    except requests.exceptions.RequestException as e:
        print(f"ОШИБКА при запросе /report: {e}")
        return False
    except Exception as e:
        print(f"ОШИБКА парсинга отчета: {e}")
        return False

def test_apply_stimulus():
    """Тестирует эндпоинт /stimulus."""
    stimulus = Stimulus()
    stimulus.emotions["любопытство"] = 0.6
    stimulus.emotions["радость"] = 0.4

    serialized_stimulus = stimulus.SerializeToString()

    headers = {'Content-Type': 'application/protobuf'}

    try:
        print("\n--- Отправка стимула: любопытство и радость ---")
        response = requests.post(f"{BASE_URL}/stimulus", data=serialized_stimulus, headers=headers)
        response.raise_for_status()

        if response.status_code == 204:
            print("Стимул успешно отправлен (Код 204 No Content).")
            return True
        else:
            print(f"Получен неожиданный статус-код: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"ОШИБКА при запросе /stimulus: {e}")
        if e.response is not None:
            print(f"  - Статус-код: {e.response.status_code}")
            print(f"  - Тело ответа: {e.response.text}")
        return False

import subprocess
import time
import sys
import os

def run_server():
    """Запускает uvicorn сервер в фоновом процессе."""
    # Используем poetry run для запуска в правильном окружении
    command = [
        "poetry", "run", "uvicorn", "sentio_engine.api.main:app",
        "--host", "0.0.0.0", "--port", "8000"
    ]
    # Запускаем в директории sentio_engine
    process = subprocess.Popen(
        command,
        cwd="sentio_engine",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(3) # Даем серверу время на запуск
    return process

def main():
    server_process = run_server()

    # Проверяем, жив ли еще сервер
    # Проверяем, не упал ли сервер сразу после запуска
    time.sleep(2) # Даем ему еще пару секунд на всякий случай
    if server_process.poll() is not None:
        print("!!! Сервер не смог запуститься. Вывод ошибок:")
        stdout, stderr = server_process.communicate()
        print("--- STDOUT ---")
        print(stdout)
        print("--- STDERR ---")
        print(stderr)
        return

    print("Сервер запущен. Начинаем тестирование...")

    try:
        if test_get_report():
            if test_apply_stimulus():
                # Запросим отчет еще раз, чтобы увидеть изменения
                test_get_report()
    finally:
        print("\nТестирование завершено. Останавливаем сервер...")
        server_process.terminate()
        server_process.wait()
        print("Сервер остановлен.")

if __name__ == "__main__":
    main()
