import json
import sys
import os

# Adjust path to import from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.mocks import MockKafkaConsumer, MockKafkaProducer, MockMagicProxy
from conductor.config import KAFKA_TOPIC_DECISIONS, KAFKA_TOPIC_ACTIONS

def run_decision_engine():
    """
    Main loop for the decision engine. Consumes decision requests from Kafka,
    uses the Magic Proxy to make a decision, and sends the resulting action
    to the execution topic.
    """
    consumer = MockKafkaConsumer(KAFKA_TOPIC_DECISIONS)
    producer = MockKafkaProducer()
    magic_proxy = MockMagicProxy()

    print("DECISION_ENGINE: Starting...")
    for message in consumer:
        try:
            request_data = json.loads(message.value)
            chat_id = request_data.get("chat_id")
            persona_manifest = request_data.get("persona_manifest")
            rag_context = request_data.get("rag_context")
            screenshots = request_data.get("screenshots")

            if not all([chat_id, persona_manifest, rag_context, screenshots is not None]):
                print("DECISION_ENGINE: ERROR - Incomplete decision request, skipping.")
                continue

            print(f"DECISION_ENGINE: Processing decision request for chat_id: {chat_id}")

            # Get decision from the Magic Proxy
            action_command = magic_proxy.decide(
                persona_manifest=persona_manifest,
                rag_context=rag_context,
                screenshots=screenshots
            )

            # Add chat_id to the final command
            action_command["chat_id"] = chat_id

            # Send the command to the execution topic
            producer.send(KAFKA_TOPIC_ACTIONS, value=json.dumps(action_command))
            producer.flush()

            print(f"DECISION_ENGINE: Sent action command for chat_id: {chat_id} to Kafka.")

        except json.JSONDecodeError:
            print("DECISION_ENGINE: ERROR - Could not decode message value.")
        except Exception as e:
            print(f"DECISION_ENGINE: ERROR - An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("Decision Engine module is ready.")