# Справочник по API

API Sentio Engine спроектирован для простоты и производительности, используя Protocol Buffers (Protobuf) для обмена данными.

## Основные эндпоинты

### `POST /stimulus`
Применяет стимул к эмоциональному состоянию движка.
*   **Тело запроса:** `Stimulus`
*   **Ответ:** `204 No Content`

### `GET /report`
Возвращает полный отчет о текущем состоянии движка.
*   **Тело ответа:** `Report`

### `POST /process_and_report` (Кэшируемый)
Комбинированный эндпоинт, который применяет стимул и немедленно возвращает отчет. Ответы кэшируются в Redis.
*   **Тело запроса:** `Stimulus`
*   **Тело ответа:** `Report`

### `POST /process_agent_text`
Обрабатывает текст от LLM-агента, ищет специальный тег `[SENTIO_EMO_STATE]` и обновляет состояние на основе найденного JSON.
*   **Тело запроса:** `{"text": "..."}`
*   **Ответ:** `204 No Content`

## Эндпоинты управления личностью

Эти эндпоинты предоставляют "API-мост" к когнитивной призме движка, позволяя внешним системам читать и динамически изменять профиль личности ИИ.

### `GET /personality`
Возвращает текущий профиль личности ИИ.
*   **Метод:** `GET`
*   **Тело ответа:** `PersonalityProfile` (Protobuf)
*   **Успешный ответ:** `200 OK`

### `POST /personality`
Обновляет профиль личности ИИ. Можно передавать как полный профиль, так и только те черты, которые нужно изменить.
*   **Метод:** `POST`
*   **Тело запроса:** `PersonalityProfile` (Protobuf)
*   **Успешный ответ:** `204 No Content`

## Служебные эндпоинты

### `GET /health`
Проверяет работоспособность сервиса.
*   **Метод:** `GET`
*   **Тело ответа:** `HealthStatus` (Protobuf)
*   **Успешный ответ:** `200 OK`

---

## Схемы Protobuf

### Основные сообщения

`Stimulus`, `Report`, `EmotionalState` (без изменений).

### Новые сообщения для управления личностью

#### `PersonalityProfile`
Представляет полный профиль личности, состоящий из карты черт.
```proto
message PersonalityProfile {
  // Карта названий черт и их данных.
  // Пример: "neuroticism": { value: 0.8, description: "..." }
  map<string, PersonalityTrait> traits = 1;
}
```

#### `PersonalityTrait`
Представляет одну черту личности.
```proto
message PersonalityTrait {
  float value = 1;        // Значение черты (0.0 до 1.0)
  string description = 2; // Описание
}
```

### Новые служебные сообщения

#### `HealthStatus`
Представляет статус работоспособности сервиса.
```proto
message HealthStatus {
  string status = 1; // Всегда "OK" при успехе
}
```

## Пример клиента (Python)

Вот расширенный пример, демонстрирующий взаимодействие с новыми эндпоинтами.

```python
import requests
from sentio_engine.schemas.sentio_pb2 import HealthStatus, PersonalityProfile, PersonalityTrait

BASE_URL = "http://127.0.0.1:8000"

# --- Проверка работоспособности ---
response = requests.get(f"{BASE_URL}/health")
if response.status_code == 200:
    health = HealthStatus()
    health.ParseFromString(response.content)
    print(f"Статус сервиса: {health.status}")

# --- Получение и обновление личности ---
response_get = requests.get(f"{BASE_URL}/personality")
if response_get.status_code == 200:
    profile = PersonalityProfile()
    profile.ParseFromString(response_get.content)
    print(f"Текущее значение нейротизма: {profile.traits['neuroticism'].value:.2f}")

    # Изменяем значение
    profile.traits['neuroticism'].value = 0.8

    # Отправляем обновленный профиль
    response_post = requests.post(
        f"{BASE_URL}/personality",
        data=profile.SerializeToString(),
        headers={'Content-Type': 'application/protobuf'}
    )
    print(f"Запрос на обновление отправлен. Код состояния: {response_post.status_code}")
```
---

**Далее:** [Конфигурация личности](./04_configuration.md)
