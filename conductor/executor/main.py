import json
import sys
import os

# Adjust path to import from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.mocks import MockKafkaConsumer
from conductor.config import KAFKA_TOPIC_ACTIONS

def run_executor():
    """
    Main loop for the executor. Consumes action commands from Kafka
    and simulates their execution.
    """
    consumer = MockKafkaConsumer(KAFKA_TOPIC_ACTIONS)

    print("EXECUTOR: Starting...")
    for message in consumer:
        try:
            command_data = json.loads(message.value)
            action = command_data.get("action")
            target = command_data.get("target")
            text = command_data.get("text")
            chat_id = command_data.get("chat_id")

            if not all([action, target, text, chat_id]):
                print("EXECUTOR: ERROR - Incomplete action command, skipping.")
                continue

            print("EXECUTOR: Received command:")
            print(f"  - Chat ID: {chat_id}")
            print(f"  - Action: {action}")
            print(f"  - Target: {target}")
            print(f"  - Text: {text}")

            # In a real scenario, this is where Playwright would be used
            # to perform the action in the browser.
            print("EXECUTOR: Simulating action execution... (e.g., typing and sending message)")
            print("EXECUTOR: Action completed successfully.")

        except json.JSONDecodeError:
            print("EXECUTOR: ERROR - Could not decode message value.")
        except Exception as e:
            print(f"EXECUTOR: ERROR - An unexpected error occurred: {e}")


if __name__ == "__main__":
    print("Executor module is ready.")