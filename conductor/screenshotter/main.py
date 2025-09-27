import json
import time
import base64
import sys
import os

# Adjust path to import from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from conductor.shared.mocks import MockKafkaProducer
from conductor.config import KAFKA_TOPIC_NOTIFICATIONS

producer = MockKafkaProducer()

def trigger_screenshot(chat_id: str):
    """
    Simulates taking a screenshot for a given chat_id and
    sending the data to a Kafka topic.
    """
    print(f"SCREENSHOTTER: Triggered for chat_id: {chat_id}")

    # Simulate taking a screenshot (a simple text as a placeholder image)
    fake_image_data = f"screenshot_for_{chat_id}_{time.time()}".encode('utf-8')
    base64_image = base64.b64encode(fake_image_data).decode('utf-8')

    message = {
        "chat_id": chat_id,
        "timestamp": time.time(),
        "screenshot_base64": base64_image
    }

    # Send message to Kafka
    producer.send(
        KAFKA_TOPIC_NOTIFICATIONS,
        value=json.dumps(message)
    )
    producer.flush()
    print(f"SCREENSHOTTER: Sent screenshot notification for chat_id: {chat_id} to Kafka.")