import json
import time
from collections import defaultdict
import threading
import sys
import os

# Adjust path to import from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.mocks import MockKafkaConsumer, MockKafkaProducer, MockRAGDatabase
from conductor.config import (
    KAFKA_TOPIC_NOTIFICATIONS,
    KAFKA_TOPIC_DECISIONS,
    ORCHESTRATOR_TIMEOUT
)

# In-memory storage for active timers and collected screenshots
ACTIVE_TIMERS = {}
SCREENSHOT_BUFFER = defaultdict(list)

# Instantiate mock components
producer = MockKafkaProducer()
rag_db = MockRAGDatabase()

def load_persona_manifest(persona_name: str = "corporate_assistant"):
    """Loads a persona manifest from the personas directory."""
    current_dir = os.path.dirname(__file__)
    # Correctly navigate to the 'conductor' directory and then to 'personas'
    personas_dir = os.path.abspath(os.path.join(current_dir, '..', 'personas'))
    manifest_path = os.path.join(personas_dir, f"{persona_name}.json")

    print(f"ORCHESTRATOR: Loading persona manifest from {manifest_path}")
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ORCHESTRATOR: ERROR - Persona manifest not found at {manifest_path}")
        return {
          "persona_name": "Default",
          "system_prompt": "You are a helpful assistant.",
          "rules": {}
        }

def process_timeout(chat_id: str):
    """
    This function is called when the timer for a chat_id expires.
    It collects data, creates a task, and sends it to the decision engine.
    """
    print(f"ORCHESTRATOR: Timeout for chat_id: {chat_id}. Processing...")

    screenshots_data = SCREENSHOT_BUFFER.pop(chat_id, [])
    if not screenshots_data:
        print(f"ORCHESTRATOR: No screenshots to process for chat_id: {chat_id}.")
        ACTIVE_TIMERS.pop(chat_id, None)
        return

    screenshots_base64 = [msg["screenshot_base64"] for msg in screenshots_data]
    persona_manifest = load_persona_manifest()
    rag_context = rag_db.get_history(chat_id)

    decision_request = {
        "chat_id": chat_id,
        "persona_manifest": persona_manifest,
        "rag_context": rag_context,
        "screenshots": screenshots_base64
    }

    producer.send(KAFKA_TOPIC_DECISIONS, value=json.dumps(decision_request))
    producer.flush()
    print(f"ORCHESTRATOR: Sent decision request for chat_id: {chat_id} to Kafka.")

    ACTIVE_TIMERS.pop(chat_id, None)

def run_orchestrator():
    """
    Main loop for the orchestrator. Consumes messages from Kafka
    and manages timers for processing.
    """
    consumer = MockKafkaConsumer(KAFKA_TOPIC_NOTIFICATIONS)
    print("ORCHESTRATOR: Starting...")
    for message in consumer:
        try:
            data = json.loads(message.value)
            chat_id = data.get("chat_id")
            if not chat_id:
                continue

            print(f"ORCHESTRATOR: Received notification for chat_id: {chat_id}")

            SCREENSHOT_BUFFER[chat_id].append(data)

            if chat_id not in ACTIVE_TIMERS:
                print(f"ORCHESTRATOR: Starting new timer for chat_id: {chat_id}")
                timer = threading.Timer(ORCHESTRATOR_TIMEOUT, process_timeout, args=[chat_id])
                ACTIVE_TIMERS[chat_id] = timer
                timer.start()
            else:
                print(f"ORCHESTRATOR: Timer already active for chat_id: {chat_id}. Buffering screenshot.")

        except json.JSONDecodeError:
            print("ORCHESTRATOR: ERROR - Could not decode message value.")
        except Exception as e:
            print(f"ORCHESTRATOR: ERROR - An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("Orchestrator module is ready.")