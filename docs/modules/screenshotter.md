# Модуль Screenshotter

## Обзор

Модуль `Screenshotter` отвечает за создание "снимков" уведомлений для заданного `chat_id` и **платформы**. В текущей реализации он имитирует этот процесс, создавая и кодируя данные в формат base64, а затем отправляя их в соответствующий топик Kafka для дальнейшей обработки.

## Функциональность

Основная задача модуля — сгенерировать событие, содержащее "снимок", и отправить его в правильный топик Kafka, в зависимости от платформы-источника.

Ключевые операции:
1.  Получает `chat_id` и `platform` от модуля `Listener` через вызов функции `trigger_screenshot`.
2.  Выбирает нужный топик Kafka (`KAFKA_TOPIC_WHATSAPP_NOTIFICATIONS` или `KAFKA_TOPIC_TELEGRAM_NOTIFICATIONS`).
3.  Имитирует создание снимка, используя `chat_id`, платформу и текущее время.
4.  Формирует сообщение в формате JSON, **добавляя в него поле `platform`**.
5.  Отправляет это сообщение в выбранный топик Kafka.

## Формат сообщения в Kafka

Сообщения, отправляемые в Kafka, имеют следующую структуру:

```json
{
  "chat_id": "some_unique_chat_id",
  "platform": "whatsapp", // или "telegram"
  "timestamp": 1678886400.0,
  "screenshot_base64": "c2NyZWVuc2hvdF9mb3Jfc29tZV91bmlxdWVfY2hhdF9pZF9vbl93aGF0c2FwcF8xNjc4ODg2NDAwLjA="
}
```

**Поля:**
*   `chat_id` (string): Уникальный идентификатор чата.
*   `platform` (string): Платформа, с которой пришло уведомление (`whatsapp` или `telegram`).
*   `timestamp` (float): Временная метка создания снимка.
*   `screenshot_base64` (string): Изображение, закодированное в base64.

## Пример использования

Модуль используется другими компонентами (`Listener`), которые вызывают его функцию.

```python
# Пример вызова из другого модуля
from conductor.screenshotter.main import trigger_screenshot

# Инициировать создание "снимка" для WhatsApp
trigger_screenshot("user123_chat456", platform="whatsapp")

# Инициировать создание "снимка" для Telegram
trigger_screenshot("789101112", platform="telegram")
```