# emotion_manager.py
import json
import re
import logging
import threading
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])
logger = logging.getLogger("EmotionManager")

EMOTION_FILE_PATH = "emotional_state.json"
file_lock = threading.Lock()

def update_emotion_from_response(full_response_text: str):
    if not isinstance(full_response_text, str):
        return
    
    pattern = r"<emotional[\s_]*state>(.*?)(?:</emotional[\s_]*state>|$)"
    match = re.search(pattern, full_response_text, re.IGNORECASE | re.DOTALL)

    if not match:
        logger.info("Тег emotional_state не найден в ответе.")
        return

    json_string = match.group(1).strip()
    logger.info(f"Найден блок для парсинга. Начало: {json_string[:100]}...")

    try:
        cleaned_string = json_string.replace('“', '"').replace('”', '"').replace("'", '"')
        cleaned_string = re.sub(r'"primarymood"', r'"primary_mood"', cleaned_string, flags=re.IGNORECASE)
        
        last_brace_index = cleaned_string.rfind('}')
        if last_brace_index != -1:
            cleaned_string = cleaned_string[:last_brace_index+1]

        logger.info("Строка после автоматической очистки готова к парсингу.")
        new_state = json.loads(cleaned_string)
        
        if "emotions" not in new_state or "primary_mood" not in new_state:
            logger.warning(f"ОШИБКА ВАЛИДАЦИИ: Отсутствуют ключи 'emotions' или 'primary_mood'. Запись отменена.")
            return

        temp_file = EMOTION_FILE_PATH + ".tmp"
        with file_lock:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(new_state, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, EMOTION_FILE_PATH)
        logger.info(f"УСПЕХ! Эмоции обновлены. Текущий mood: {new_state.get('primary_mood')}")

    except json.JSONDecodeError as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА ПАРСИНГА JSON: {e}")
        logger.error(f"Проблемный контент (после очистки): {cleaned_string}")
    except Exception as e:
        logger.exception("Произошла непредвиденная критическая ошибка")