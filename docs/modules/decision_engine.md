# Модуль Decision Engine

## Обзор

Модуль `Decision Engine` (Механизм принятия решений) является "мозгом" системы Conductor. Он отвечает за анализ данных, собранных `Orchestrator`, и определение следующего действия, которое должна выполнить система.

## Функциональность

Основная задача модуля — принять запрос на решение, обработать его с помощью `MockMagicProxy` (имитатора AI-компонента) и отправить команду на исполнение в `Executor`.

Ключевые операции:
1.  **Прослушивание Kafka**: Потребляет сообщения из топика `KAFKA_TOPIC_DECISIONS`.
2.  **Анализ данных**: Извлекает из сообщения `chat_id`, **`platform`**, `persona_manifest`, `rag_context` и `screenshots`.
3.  **Принятие решения**: Передает полученные данные в `MockMagicProxy`, который возвращает команду.
4.  **Формирование команды**: Добавляет **`chat_id` и `platform`** к команде, чтобы `Executor` знал, где и через какой мессенджер нужно выполнить действие.
5.  **Отправка команды на исполнение**: Отправляет итоговую команду в топик Kafka `KAFKA_TOPIC_ACTIONS`.

## Формат входящего сообщения (из Orchestrator)

```json
{
  "chat_id": "some_unique_chat_id",
  "platform": "telegram",
  "persona_manifest": { "..._details_..." },
  "rag_context": "...",
  "screenshots": [ "base64_screenshot_1", "..." ]
}
```

## Формат исходящего сообщения (для Executor)

```json
{
  "action": "send_message",
  "target": "@all",
  "text": "Hello! How can I help you today?",
  "chat_id": "some_unique_chat_id",
  "platform": "telegram"
}
```

**Поля:**
*   `action` (string): Действие, которое нужно выполнить.
*   `target` (string): Цель действия.
*   `text` (string): Текст для отправки.
*   `chat_id` (string): Идентификатор чата.
*   `platform` (string): Платформа для выполнения действия (`whatsapp` или `telegram`).